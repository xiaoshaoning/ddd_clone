from setuptools import setup, find_packages

setup(
    name="ddd-clone",
    version="0.1.0",
    description="A graphical debugger frontend for GDB",
    author="DDD Clone Team",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0",
        "PyQt5>=5.15.0",
        "pexpect>=4.8.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "ddd-clone=ddd_clone.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)