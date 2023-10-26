"""Loads Files from Dropbox."""

import tempfile
from typing import List
import pathlib

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from langchain.document_loaders import Docx2txtLoader
from langchain.document_loaders import UnstructuredExcelLoader
from langchain.document_loaders import UnstructuredPowerPointLoader
from langchain.document_loaders import UnstructuredMarkdownLoader
from striprtf.striprtf import rtf_to_text

ALLOWED_EXTENSIONS = [
    "md",
    "htm",
    "html",
    "docx",
    "xls",
    "xlsx",
    "pptx",
    "pdf",
    "rtf",
    "txt",
]

class DropboxLoader(BaseLoader):
    """Loading logic for Dropbox files."""

    def __init__(self, auth: str, app_key: str = None, app_secret: str = None, folder_path: str = None, file_paths: List = None, file_path: str = None):
        """Initialize with auth.

        Args:
            auth: Dropbox auth token dict, contains:
                {
                    "access": "ACCESS_TOKEN_FROM_OAUTH",
                    "refresh": "REFRESH_TOKEN",
                    "id_token": "ID_TOKEN_NOT_USED",
                    "expire": "EXPIRE_TIMESTAMP"
                }

            To use the refresh token, optionally pass in:
                app_key
                app_secret

            One of the following:
                folder_path: Path to a folder in the Dropbox account. If the root folder, an empty string
                file_paths: List of paths to files in Dropbox
                file_path: A single file path to a file in Dropbox
        """
        self.auth = auth
        self.app_key = app_key
        self.app_secret = app_secret

        self.folder_path = None
        self.file_paths = None
        self.file_path = None

        if folder_path is not None:
            self.folder_path = folder_path
        elif file_paths is not None:
            self.file_paths = file_paths
        else:
            self.file_path = file_path

        self.invalid_files = []

        self.errors = []

    def _get_html_as_string(self, html) -> str:

        try:
            # Import the html parser class
            from bs4 import BeautifulSoup
        except ImportError as exp:
            raise ImportError(
                "Could not import beautifulsoup4 python package. "
                "Please install it with `pip install beautifulsoup4`."
            ) from exp

        html_string = BeautifulSoup(html, "lxml").text.strip()

        return html_string

    def _load_text_file(self, file_path, download_path) -> List[Document]:
        filename = pathlib.Path(download_path).name
        file_contents = pathlib.Path(download_path).read_text()

        return [Document(
            page_content=file_contents.strip(),
            metadata={ "source": f"dropbox://{file_path}", "filename": filename, "kind": "file" }
        )]

    def _load_html_file(self, file_path, download_path) -> List[Document]:
        file_contents = pathlib.Path(download_path).read_text()

        return [Document(
            page_content=self._get_html_as_string(file_contents),
            metadata={ "source": f"dropbox://{file_path}", "kind": "file" }
        )]

    def _load_rtf_file(self, file_path, download_path) -> List[Document]:
        file_contents = pathlib.Path(download_path).read_text()

        return[Document(
            page_content=rtf_to_text(file_contents).strip(),
            metadata={ "source": f"dropbox://{file_path}", "kind": "file" }
        )]

    def _load_pdf_file(self, file_path, download_path) -> List[Document]:
        try:
            # Import PDF parser class
            from PyPDF2 import PdfReader
        except ImportError as exp:
            raise ImportError(
                "Could not import PyPDF2 python package. "
                "Please install it with `pip install PyPDF2`."
            ) from exp

        pdf_reader = PdfReader(download_path)

        docs = []

        for i, page in enumerate(pdf_reader.pages):
            docs.append(Document(
                page_content=page.extract_text(),
                metadata={ "source": f"dropbox://{file_path}", "kind": "file", "page": i+1 }
            ))

        return docs

    def _load_docx_file(self, file_path, download_path) -> List[Document]:
        loader = Docx2txtLoader(download_path)
        docs = loader.load()

        return docs

    def _load_excel_file(self, file_path, download_path) -> List[Document]:
        loader = UnstructuredExcelLoader(download_path)
        docs = loader.load()

        return docs

    def _load_pptx_file(self, file_path, download_path) -> List[Document]:
        loader = UnstructuredPowerPointLoader(download_path)
        docs = loader.load()

        return docs

    def _load_md_file(self, file_path, download_path) -> List[Document]:
        loader = UnstructuredMarkdownLoader(download_path)
        docs = loader.load()

        return docs

    def _load_file(self, dbx, file_path) -> List[Document]:
        import dropbox

        file_documents = []

        file_extension = pathlib.Path(file_path).suffix.replace('.', '')
        file_name = pathlib.Path(file_path).stem

        if file_extension in ALLOWED_EXTENSIONS:
            # Download file
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = f"{temp_dir}/{file_name}"

                try:
                    dbx.files_download_to_file(download_path=download_path, path=file_path)

                    if file_extension == "txt":
                        file_documents = file_documents + self._load_text_file(file_path, download_path)

                    if file_extension in [ "htm", "html" ]:
                        file_documents = file_documents + self._load_html_file(file_path, download_path)

                    elif file_extension == "pdf":
                        file_documents = file_documents + self._load_pdf_file(file_path, download_path)

                    elif file_extension == "docx":
                        file_documents = file_documents + self._load_docx_file(file_path, download_path)

                    elif file_extension in [ "xlsx", "xls" ]:
                        file_documents = file_documents + self._load_excel_file(file_path, download_path)

                    elif file_extension == "pptx":
                        file_documents = file_documents + self._load_pptx_file(file_path, download_path)

                    elif file_extension == "md":
                        file_documents = file_documents + self._load_md_file(file_path, download_path)

                    elif file_extension == "rtf":
                        file_documents = file_documents + self._load_rtf_file(file_path, download_path)

                except dropbox.exceptions.DropboxException as error:
                    self.errors.append({ "message": error.error, "file": file_path })

        else:
            self.invalid_files.append()

        # Replace null character with space
        for doc in file_documents:
            doc.page_content = doc.page_content.replace('\x00', ' ')

        return file_documents

    def _load_files_from_folder_path(self, dbx, folder_path) -> List[Document]:
        import dropbox

        file_documents = []

        files = None
        found_all_records = False
        file_paths = []

        try:
            while found_all_records is False:
                if files is None:
                    files = dbx.files_list_folder(folder_path,
                        recursive=True,
                        include_deleted=False,
                    )
                else:
                    files = dbx.files_list_folder_continue(files.cursor)

                for file in files.entries:
                    if isinstance(file, dropbox.files.FileMetadata):
                        file_extension = pathlib.Path(file.name).suffix.replace('.', '')

                        if file_extension in ALLOWED_EXTENSIONS:
                            file_paths.append(file.path_lower)

                        else:
                            self.invalid_files.append(file.path_display)

                if files.has_more is False:
                    found_all_records = True

            file_documents = self._load_files_from_paths(
                dbx = dbx,
                file_paths = file_paths
            )
        except dropbox.exceptions.DropboxException as error:
            self.errors.append({ "message": error.error, "folder": folder_path })

        return file_documents

    def _load_files_from_paths(self, dbx, file_paths) -> List[Document]:
        file_documents = []

        for file_path in file_paths:
            file_documents = file_documents + self._load_file(
                dbx = dbx,
                file_path = file_path
            )

        return file_documents

    def load(self) -> List[Document]:
        """Load files."""
        try:
            # Import the Dropbox SDK
            import dropbox
        except ImportError as exp:
            raise ImportError(
                "Could not import dropbox python package. "
                "Please install it with `pip install dropbox`."
            ) from exp

        args = {
            "oauth2_access_token": self.auth['access']
        }

        # If an app_key + secret is specified, pass in refresh token, app_key, app_secret
        if self.app_key is not None and self.app_secret is not None:
            args['oauth2_refresh_token'] = self.auth['refresh']
            args['app_key'] = self.auth['app_key']
            args['app_secret'] = self.auth['app_secret']

        # Initialize a new Dropbox object
        try:
            with dropbox.Dropbox(
                **args
                # =self.token[''],
                # oauth2_access_token_expiration=self.token['expire'],
            ) as dbx:
                if self.folder_path is not None:
                    return self._load_files_from_folder_path(
                        dbx = dbx,
                        folder_path = self.folder_path
                    )

                if self.file_paths is not None:
                    return self._load_files_from_paths(
                        dbx = dbx,
                        file_paths = self.file_paths
                    )

                return self._load_file(
                    dbx = dbx,
                    file_path = self.file_path
                )
        except dropbox.exceptions.DropboxException as error:
            self.errors.append({ "message": error.error })

        return []
