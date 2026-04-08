from planner.pddl_generator import build_domain_pddl

domain_text = build_domain_pddl()

with open("domain.pddl", "w", encoding="utf-8") as f:
    f.write(domain_text)

print("domain.pddl saved")