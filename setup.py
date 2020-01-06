from pathlib import Path

from setuptools import setup, find_packages

CURRENT_DIR = Path(__file__).parent


def get_long_description() -> str:
    readme = CURRENT_DIR / "README.rst"
    with open(readme) as file:
        return file.read()


def get_version() -> str:
    version = CURRENT_DIR / "VERSION"
    with open(version) as file:
        return file.readline()


EXTRAS_REQUIRE = {"test": ["pytest"]}
EXTRAS_REQUIRE["dev"] = EXTRAS_REQUIRE["test"] + ["pre-commit", "flake8>=3.7.9", "tox"]

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
    version=get_version(),
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
