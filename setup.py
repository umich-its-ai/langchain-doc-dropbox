from setuptools import setup, find_packages


def load_requirements(path: str) -> list[str]:
    with open(path, encoding="utf-8") as req_file:
        return [
            line.strip()
            for line in req_file
            if line.strip() and not line.startswith("#")
        ]


setup(
    name="dropbox_langchain",
    version="0.13.0",
    description="A Dropbox langchain integration",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="University of Michigan",
    author_email="noreply@umich.edu",
    url="https://github.com/umich-its-ai/langchain-doc-dropbox",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License (GPL)",
    ],
    install_requires=load_requirements("requirements.txt"),
    python_requires=">=3.8.1",
)
