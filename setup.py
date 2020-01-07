import re
from pathlib import Path

from setuptools import setup, find_packages

CURRENT_DIR = Path(__file__).parent


def get_long_description() -> str:
    readme = CURRENT_DIR / "README.rst"
    with open(readme) as file:
        return file.read()


def find_version(fname, var_name="__version__") -> str:
    """Attempts to find the version number in the file names fname.
    Raises RuntimeError if not found.
    """
    version = None
    regex = re.compile(rf'{var_name} = [\'"]([^\'"]*)[\'"]')

    with open(fname, "r") as file:
        for line in file:
            match = regex.match(line)
            if match:
                version = match.group(1)
                break
    if not version:
        raise RuntimeError("Cannot find version information.")
    return version


EXTRAS_REQUIRE = {
    "test": ["pytest==5.3.2", "pytest-cov==2.8.1"],
    "docs": ["sphinx==2.3.1", "sphinx-autodoc-typehints==1.10.3"],
}
EXTRAS_REQUIRE["dev"] = (
    EXTRAS_REQUIRE["test"]
    + EXTRAS_REQUIRE["docs"]
    + ["pre-commit==1.21.0", "flake8==3.7.9", "tox==3.14.3"]
)


setup(
    name="gimme-that",
    description="Simple and flexible dependency injection framework.",
    long_description=get_long_description(),
    long_description_content_type="text/x-rst",
    keywords="inversion-of-control IoC DI dependency-injection",
    author="Pelle Koster",
    url="https://github.com/elfjes/gimme-that",
    license="MIT",
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.6",
    extras_require=EXTRAS_REQUIRE,
    test_suite="tests",
    version=find_version("src/gimme/__init__.py"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Libraries",
    ],
)
