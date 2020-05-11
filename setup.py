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
    package_data={'': ['*.tx']},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires = [
        'textX          >= 2.1.0,  < 2.2.0',
        'clipspy        >= 0.3.3,  < 0.4.0',
        'Flask          >= 1.1.2,  < 1.2.0',
        'Flask-PyMongo  >= 2.3.0,  < 2.4.0',
        'Flask-Cors     >= 3.0.8,  < 3.1.0',
        'requests       >= 2.23.0, < 2.24.0',
        'jsonpath-ng    >= 1.5.1,  < 1.6.0',
    ]
    
)