from __future__ import annotations

"""
sandbox for running code in current environment
"""

from pathlib import Path
import subprocess
import sys
import os
import shutil
import ast
import importlib.util
from typing import Optional
from .console import console


class REPL:
    """Manages sandbox environment for code execution in current environment"""

    def __init__(self):
        self.current_dir = Path.cwd()
        self.sandbox_dir = self.current_dir / ".sandbox"
        self.has_uv = False

    def ensure_sandbox(self):
        """Ensures sandbox directory exists"""
        if not self.sandbox_dir.exists():
            self.sandbox_dir.mkdir(parents=True)

    def get_python(self) -> str:
        """Gets path to current Python executable"""
        return sys.executable

    def get_pip(self) -> str:
        """Gets path to current pip executable"""
        if sys.platform == "win32":
            return str(Path(sys.executable).parent / "pip.exe")
        return str(Path(sys.executable).parent / "pip")

    def install_uv(self):
        """Installs uv package manager if needed"""
        if not self.has_uv:
            subprocess.run([self.get_pip(), "install", "uv"], check=True)
            self.has_uv = True

    def get_uv_path(self) -> str:
        """Gets path to uv executable"""
        return str(
            Path(sys.executable).parent
            / ("uv.exe" if sys.platform == "win32" else "uv")
        )

    def is_stdlib_module(self, module_name: str) -> bool:
        """Check if a module is part of the Python standard library"""
        known_third_party = {
            "numpy",
            "pandas",
            "requests",
            "sklearn",
            "tensorflow",
            "torch",
            "matplotlib",
            "scipy",
            "seaborn",
        }

        if module_name in known_third_party:
            return False

        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return False

        if module_name in sys.modules:
            module = sys.modules[module_name]
            if hasattr(module, "__file__"):
                return (
                    module.__file__ is not None
                    and "site-packages" not in module.__file__
                )

        if spec.origin:
            return "site-packages" not in spec.origin

        return True

    def extract_imports(self, code: str) -> list[str]:
        """Extracts required package names from import statements"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        packages = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    packages.add(name.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    packages.add(node.module.split(".")[0])

        return list(packages)

    def install_package(self, package: str):
        """Installs a package using uv"""
        self.install_uv()

        env_vars = os.environ.copy()
        try:
            # Remove capture_output to see UV's spinner and output
            subprocess.run(
                [self.get_uv_path(), "pip", "install", package],
                check=True,
                env=env_vars,
            )

            # Verify the package can be imported
            verify_cmd = [self.get_python(), "-c", f"import {package.split('[')[0]}"]

            # Keep verification quiet
            subprocess.run(
                verify_cmd, check=True, env=env_vars, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to install or verify package {package}: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            )

    def execute_code(self, code: str, required_packages: Optional[list[str]] = None):
        """Executes code in current environment"""
        self.ensure_sandbox()

        # Auto-detect required packages from code
        detected_packages = self.extract_imports(code)
        all_packages = list(set(detected_packages + (required_packages or [])))

        # Install required packages if specified
        packages_installed = False
        if all_packages:
            for package in all_packages:
                # Skip standard library modules
                if self.is_stdlib_module(package):
                    continue
                try:
                    self.install_package(package)
                    packages_installed = True
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"Failed to install package {package}: {str(e)}")

        # If we installed new packages, verify imports
        if packages_installed:
            setup_code = "\n".join(
                [f"import {pkg.split('[')[0]}" for pkg in all_packages]
            )
            verification_code = setup_code + "\nprint('Package imports successful')"

            verify_file = self.sandbox_dir / "verify_imports.py"
            try:
                with verify_file.open("w") as f:
                    f.write(verification_code)

                result = subprocess.run(
                    [self.get_python(), str(verify_file)],
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    raise RuntimeError(f"Package verification failed:\n{result.stderr}")
            finally:
                if verify_file.exists():
                    verify_file.unlink()

        # Create temporary file for code execution
        temp_file = self.sandbox_dir / "temp_code.py"
        try:
            with temp_file.open("w") as f:
                f.write(code)

            # Execute code
            result = subprocess.run(
                [self.get_python(), str(temp_file)], capture_output=True, text=True
            )

            if result.returncode != 0:
                raise RuntimeError(f"Code execution failed:\n{result.stderr}")

            return result.stdout

        finally:
            if temp_file.exists():
                temp_file.unlink()

    def cleanup(self):
        """Cleans up sandbox directory"""
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir)

    def reset(self):
        """Resets sandbox directory"""
        self.cleanup()
        self.ensure_sandbox()


# repl singleton
_sandbox_manager = REPL()


def execute_in_sandbox(
    code: str,
    required_packages: Optional[list[str]] = None,
    reset: bool = False,
    verbose: bool = False,
    return_result: bool = False,
) -> str:
    """
    Executes code in current environment sandbox

    Args:
        code: Python code to execute
        required_packages: List of packages required by the code
        reset: Whether to reset sandbox before execution
        verbose: Whether to print verbose output
        return_result: Whether to return the Python object instead of stdout

    Returns:
        Execution output or Python object if return_result=True
    """
    if verbose:
        console.message("[bold blue]Executing code in sandbox...[/bold blue]")

    if reset:
        if verbose:
            console.message("[yellow]Resetting sandbox...[/yellow]")
        _sandbox_manager.reset()

    try:
        if return_result:
            # Execute in the current process to get the actual object
            local_vars = {}
            exec(code, globals(), local_vars)
            return local_vars.get("result")
        else:
            output = _sandbox_manager.execute_code(code, required_packages)

        if verbose:
            console.message("[bold green]Code executed successfully![/bold green]")
        return output
    except Exception as e:
        if verbose:
            console.message(f"[bold red]Error executing code: {str(e)}[/bold red]")
        raise


if __name__ == "__main__":
    # Example usage
    code = """
import pandas as pd

df = pd.DataFrame({
    'A': [1, 2, 3],
    'B': [4, 5, 6]
})
print(df)
"""

    result = execute_in_sandbox(code, verbose=True)
    print("Output:", result)
