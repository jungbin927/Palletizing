from configs.default_config import EnvConfig 
from env.pallet_env import PalletLoadingEnv 

from planner.symbolic_policy import SymbolicPolicy 
from planner.external_planner import ExternalPlanner 
from planner.plan_parser import PlanParser 
from planner.pddl_generator import build_problem_pddl 

class SimplePDDLGenerator: 
    def __init__(self, env): 
        self.env = env 
        
    def generate(self, obs, candidate_actions): 
        return build_problem_pddl(self.env.export_planner_state()) 
    
def main(): 
    config = EnvConfig() 
    env = PalletLoadingEnv(config) 
    env.reset() 
    
    pddl_generator = SimplePDDLGenerator(env) 
    external_planner = ExternalPlanner( 
        domain_file_path="domain.pddl", 
        docker_image="aibasel/downward", 
        search_config="astar(lmcut())", 
    ) 
    plan_parser = PlanParser() 
    
    policy = SymbolicPolicy( 
        env=env, 
        pddl_generator=pddl_generator,
        external_planner=external_planner, 
        plan_parser=plan_parser, 
    ) 
    step_count = 0 
    max_test_steps = 50 
    
    while not env.state.done and step_count < max_test_steps: 
        print(f"\n========== STEP {step_count} ==========") 
        # 1. 새 박스 도착 
        box = env.get_next_arrival() 
        if box is not None: 
            added = env.add_to_buffer(box) 
            print("[ARRIVAL]", box.box_id, box.region, "buffer_added=", added) 
            
        # 2. 현재 observation 
        obs = env.observe() 
        print("[OBS buffer_size]", obs["buffer_size"]) 
        print("[OBS processed_box_count]", obs["processed_box_count"]) 
        
        # 3. planner action 선택 
        action = policy.select_action(obs) 
        print("[ACTION]", action) 
        
        # 4. action 실행 
        next_obs, result = env.step(action) 
        print("[RESULT]", result)
        print("[NEXT OBS buffer_size]", next_obs["buffer_size"]) 
        print("[NEXT OBS processed_box_count]", next_obs["processed_box_count"]) 
        
        # 5. 현재 open pallet 상태 요약 
        for pallet in env.state.open_pallets: 
            print( 
                  " [PALLET]", pallet.pallet_id, 
                  "region=", pallet.region, 
                  "boxes=", pallet.num_boxes, 
                  "weight=", pallet.total_weight, 
                  "height=", pallet.used_height, ) 
            
        step_count += 1 
            
        print("\n========== FINAL ==========") 
        print("processed_boxes:", env.state.processed_boxes)
        print("done:", env.state.done) 
        
        print("\n[FINAL PALLETS]") 
        for pallet in env.state.open_pallets + env.state.finished_pallets: 
            print( 
                  pallet.pallet_id, 
                  "region=", pallet.region, 
                  "boxes=", pallet.num_boxes, 
                  "weight=", pallet.total_weight, 
                  "height=", pallet.used_height, 
                ) 
            
if __name__ == "__main__": main()
