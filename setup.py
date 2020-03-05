import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='akashic',
    version='0.0.1',
    author='Lazar Marković',
    author_email='lazar.kmarkovic@gmail.com',
    description="Rule based web API framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lazarmarkovic/akashic",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)