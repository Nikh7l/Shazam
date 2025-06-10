from setuptools import setup, find_packages

setup(
    name="shazam_clone",
    version="0.1",
    packages=find_packages(where="backend"),
    package_dir={"": "backend"},
    install_requires=[
        'numpy',
        'scipy',
        'pydub',
    ],
    python_requires='>=3.8',
)
