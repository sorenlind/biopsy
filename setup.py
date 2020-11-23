"""Setup script for package."""
import re

from setuptools import find_packages, setup

match = re.search(r'^VERSION\s*=\s*"(.*)"', open("biopsy/version.py").read(), re.M)
VERSION = match.group(1) if match else "???"
with open("README.md", "rb") as f:
    LONG_DESCRIPTION = f.read().decode("utf-8")

setup(
    name="biopsy",
    version=VERSION,
    description="Package for preprocessing ndpi and ndpa files.",
    long_description=LONG_DESCRIPTION,
    author="Soren Lind Kristiansen",
    author_email="soren@gutsandglory.dk",
    url="",
    keywords="",
    packages=find_packages(),
    install_requires=["lxml", "openslide-python", "Pillow", "tqdm"],
    extras_require={
        "dev": [
            "black",
            "flake8",
            "jupyter",
            "lxml-stubs",
            "mypy",
            "pycodestyle",
            "pydocstyle",
            "pylint",
            "rope",
            "pytest",
        ],
        "test": ["coverage", "pytest", "pytest-cov", "tox"],
    },
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
    ],
    entry_points={"console_scripts": ["biopsy = biopsy.__main__:main"]}
)
