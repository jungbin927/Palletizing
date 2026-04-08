# planner/external_planner.py

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional
import tempfile
from typing import Dict

from planner.pddl_generator import export_pddl_files
from planner.plan_parser import PlanParser

class ExternalPlanner:
    # 문제 파일만 문자열로 받고, domain은 domain_fil_path에서 읽는 구조
    '''
    1. 임시 폴더 생성
    2. 거기에 problem.pddl, domain.pddl 저장
    3. docker run --rm -v <tmpdir>:/benchmarks aibasel/downward ... 실행
    4. stdout/stderr 반환
    '''

    def __init__(
        self,
        domain_file_path: str,
        docker_image: str = "aibasel/downward",
        search_config: str = "astar(lmcut())",
    ):
        self.domain_file_path = domain_file_path
        self.docker_image = docker_image
        self.search_config = search_config

    def run(self, problem_text: str) -> Dict:
        with tempfile.TemporaryDirectory() as tmpdir:
            problem_path = os.path.join(tmpdir, "problem.pddl")
            domain_path = os.path.join(tmpdir, "domain.pddl")
            

            with open(problem_path, "w", encoding="utf-8") as f:
                f.write(problem_text)

            with open(self.domain_file_path, "r", encoding="utf-8") as f:
                domain_text = f.read()

            with open(domain_path, "w", encoding="utf-8") as f:
                f.write(domain_text)

            docker_mount = tmpdir.replace("\\", "/")
            if ":" in docker_mount:
                drive = docker_mount[0].lower()
                docker_mount = f"/{drive}{docker_mount[2:]}"
            # Windows Docker Desktop path 보정이 애매하면
            # 일단 subprocess shell=True 대신 cwd와 절대경로로 관리하는 방식도 가능

            cmd = [
                "docker", "run", "--rm",
                "-v", f"{tmpdir}:/benchmarks",
                self.docker_image,
                "/benchmarks/domain.pddl",
                "/benchmarks/problem.pddl",
                "--search", self.search_config
            ]
            
            print("[DEBUG] tmpdir =", tmpdir)
            print("[DEBUG] docker cmd =", " ".join(cmd))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "plan_text": "",
                    "stderr": result.stderr,
                    "stdout": result.stdout,
                }

            return {
                "success": True,
                "plan_text": result.stdout,
                "stderr": result.stderr,
                "stdout": result.stdout,
            }

'''
class FastDownwardPlanner:
    """
    Fast Downward 외부 planner wrapper.

    사용 방식:
    1. 현재 planner_state를 받아 domain/problem pddl 파일 생성
    2. fast-downward.py 실행
    3. 결과 plan 파일을 읽어서 action dict list로 반환
    """

    def __init__(
        self,
        fd_py_path: str,
        work_dir: str = "planner_tmp",
        search_option: str = "astar(lmcut())",
    ):
        """
        Parameters
        ----------
        fd_py_path : str
            fast-downward.py 경로
            예: "C:/fast-downward/fast-downward.py"

        work_dir : str
            pddl 및 plan 파일을 저장할 작업 디렉토리

        search_option : str
            Fast Downward search 옵션
        """
        self.fd_py_path = Path(fd_py_path)
        self.work_dir = Path(work_dir)
        self.search_option = search_option

        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.domain_path = self.work_dir / "domain.pddl"
        self.problem_path = self.work_dir / "problem.pddl"
        self.plan_path = self.work_dir / "sas_plan"

    def export_problem(self, planner_state: dict) -> None:
        """
        현재 planner_state 기반으로 domain/problem pddl 파일 저장
        """
        export_pddl_files(
            planner_state=planner_state,
            domain_path=str(self.domain_path),
            problem_path=str(self.problem_path),
        )

    def run(self, planner_state: dict) -> list[dict]:
        """
        planner 실행 후 action list 반환
        실패 시 빈 리스트 반환
        """
        self.export_problem(planner_state)

        # 기존 plan 파일 삭제
        if self.plan_path.exists():
            self.plan_path.unlink()

        cmd = [
            "python",
            str(self.fd_py_path),
            str(self.domain_path),
            str(self.problem_path),
            "--search",
            self.search_option,
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as e:
            print("[FastDownwardPlanner] 실행 예외:", e)
            return []

        print("\n[FastDownward stdout]")
        print(result.stdout)

        if result.stderr:
            print("\n[FastDownward stderr]")
            print(result.stderr)

        if not self.plan_path.exists():
            print("[FastDownwardPlanner] plan 파일이 생성되지 않았음.")
            return []

        plan_text = self.plan_path.read_text(encoding="utf-8")
        actions = PlanParser.parse_plan_text(plan_text)
        return actions

    def get_domain_problem_paths(self) -> tuple[str, str]:
        return str(self.domain_path), str(self.problem_path)

    def get_plan_path(self) -> str:
        return str(self.plan_path)
'''