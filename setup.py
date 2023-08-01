from setuptools import setup, find_packages

setup(
    name='dropbox_langchain',
    version='0.1',
    description='A Dropbox langchain integration',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='University of Michigan',
    author_email='noreply@umich.edu',
    url='https://github.com/umich-its-ai/langchain-doc-dropbox',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License (GPL)'
    ],
    install_requires=[
        'langchain',
        'unstructured',
        'dropbox',
        'beautifulsoup4',
        'lxml',
        'PyPDF2',
        'docx2txt',
        'striprtf'
    ],
    python_requires='>=3.8.1',
)
