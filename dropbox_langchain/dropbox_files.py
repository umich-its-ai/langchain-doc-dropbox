"""Loads Files from Dropbox."""

import tempfile
import json
from typing import Any, List, Literal
from pydantic import BaseModel
import pathlib

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader

from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.document_loaders import UnstructuredExcelLoader
from langchain_community.document_loaders import UnstructuredPowerPointLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader

from striprtf.striprtf import rtf_to_text

import logging
logger = logging.getLogger(__name__)

ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

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
    "paper"
]


class LogStatement(BaseModel):
    """
    INFO can be user-facing statements, non-technical and perhaps very high-level
    """
    message: Any
    level: Literal['INFO', 'DEBUG', 'WARNING']

    def __json__(self):
        return {
            'message': self.message,
            'level': self.level,
        }


class DropboxLoader(BaseLoader):
    """Loading logic for Dropbox files."""

    def __init__(self, auth: dict, app_key: str = None, app_secret: str = None, folder_path: str = None, file_paths: List = None, file_path: str = None, is_team_folder: bool = False):
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
        self.is_team_folder = is_team_folder

        if folder_path is not None:
            self.folder_path = folder_path
        elif file_paths is not None:
            self.file_paths = file_paths
        else:
            self.file_path = file_path

        self.invalid_files = []

        self.errors = []
        self.progress = []

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

    def _load_text_file(self, file_path, download_path, source) -> List[Document]:
        filename = pathlib.Path(download_path).name
        file_contents = pathlib.Path(download_path).read_text()

        return [Document(
            page_content=file_contents.strip(),
            metadata={ "source": source, "filename": filename, "kind": "file" }
        )]

    def _load_html_file(self, file_path, download_path, source) -> List[Document]:
        file_contents = pathlib.Path(download_path).read_text()

        return [Document(
            page_content=self._get_html_as_string(file_contents),
            metadata={ "source": source, "kind": "file" }
        )]

    def _load_rtf_file(self, file_path, download_path, source) -> List[Document]:
        file_contents = pathlib.Path(download_path).read_text()

        return [Document(
            page_content=rtf_to_text(file_contents).strip(),
            metadata={ "source": source, "kind": "file" }
        )]

    def _load_pdf_file(self, file_path, download_path, source) -> List[Document]:
        try:
            # Import PDF parser class
            from PyPDF2 import PdfReader
            from PyPDF2 import errors
            from binascii import Error as binasciiError
        except ImportError as exc:
            raise ImportError(
                "Could not import PyPDF2 python package. "
                "Please install it with `pip install PyPDF2`."
            ) from exc

        docs = []

        try:
            pdf_reader = PdfReader(download_path)

            for i, page in enumerate(pdf_reader.pages):
                docs.append(Document(
                    page_content=page.extract_text(),
                    metadata={"source": source, "kind": "file", "page": i+1}
                ))
        except errors.FileNotDecryptedError as err:
            self._error_logger(error=f"PyPDF2.errors.FileNotDecryptedError: File has not been decrypted ({file_path})", action="read_pdf", entity_type="file")
            self.logMessage(message={"message": {'filename': f"{file_path}", 'reason': 'not_indexed'}}, level='INFO')
        except binasciiError as err:
            self._error_logger(error=f"{str(err)} ({file_path})", action="read_pdf", entity_type="file")
            self.logMessage(message={"message": {'filename': f"{file_path}", 'reason': 'not_indexed'}}, level='INFO')
        except Exception as err:
            self._error_logger(error=f"{str(err)} ({file_path})", action="read_pdf", entity_type="file")
            self.logMessage(message={"message": {'filename': f"{file_path}", 'reason': 'not_indexed'}}, level='INFO')

        return docs

    def _load_docx_file(self, file_path, download_path, source) -> List[Document]:
        loader = Docx2txtLoader(download_path)
        docs = loader.load()

        return self._normalize_docs(docs, source)

    def _load_excel_file(self, file_path, download_path, source) -> List[Document]:
        loader = UnstructuredExcelLoader(download_path)
        docs = loader.load()

        return self._normalize_docs(docs, source)

    def _load_pptx_file(self, file_path, download_path, source) -> List[Document]:
        loader = UnstructuredPowerPointLoader(download_path)
        docs = loader.load()

        return self._normalize_docs(docs, source)

    def _load_md_file(self, file_path, download_path, source) -> List[Document]:
        loader = UnstructuredMarkdownLoader(download_path)
        docs = loader.load()
        return self._normalize_docs(docs, source)

    def _normalize_docs(self, docs, source) -> List[Document]:
        for doc in docs:
            doc.metadata['source'] = source
            doc.metadata['kind'] = "file"

        return docs

    def _load_file(self, dbx, file_path) -> List[Document]:
        self.logMessage(message=f"Processing ({file_path})", level="DEBUG")

        import dropbox

        file_documents = []

        file_extension = pathlib.Path(file_path).suffix.replace('.', '')
        file_name = pathlib.Path(file_path).stem

        # Calculate source link (use https and preview link format - dropbox:// protocol isn't guaranteed to work)
        path_obj = pathlib.Path(file_path[1:])
        folders = path_obj.parts
        folders = '/'.join(folders[:-1])
        source = f"https://www.dropbox.com/home/{folders}?preview={path_obj.name}"

        if file_extension in ALLOWED_EXTENSIONS:
            if file_extension == "paper":
                # Download file
                with tempfile.TemporaryDirectory() as temp_dir:
                    download_path = f"{temp_dir}/{file_name}"

                    try:
                        dbx.files_export_to_file(download_path=download_path, path=file_path, export_format="markdown")
                        file_documents = file_documents + self._load_md_file(file_path, download_path, source)
                    except dropbox.exceptions.DropboxException as error:
                        self.logMessage(message={"message": error.error, "file": file_path}, level='WARNING')
            else:
                # Download file
                with tempfile.TemporaryDirectory() as temp_dir:
                    download_path = f"{temp_dir}/{file_name}"

                    try:
                        dbx.files_download_to_file(download_path=download_path, path=file_path)

                        if file_extension == "txt":
                            file_documents = file_documents + self._load_text_file(file_path, download_path, source)

                        if file_extension in ["htm", "html"]:
                            file_documents = file_documents + self._load_html_file(file_path, download_path, source)

                        elif file_extension == "pdf":
                            file_documents = file_documents + self._load_pdf_file(file_path, download_path, source)

                        elif file_extension == "docx":
                            file_documents = file_documents + self._load_docx_file(file_path, download_path, source)

                        elif file_extension in ["xlsx", "xls"]:
                            file_documents = file_documents + self._load_excel_file(file_path, download_path, source)

                        elif file_extension == "pptx":
                            file_documents = file_documents + self._load_pptx_file(file_path, download_path, source)

                        elif file_extension == "md":
                            file_documents = file_documents + self._load_md_file(file_path, download_path, source)

                        elif file_extension == "rtf":
                            file_documents = file_documents + self._load_rtf_file(file_path, download_path, source)

                    except dropbox.exceptions.DropboxException as error:
                        self.logMessage(message={"message": error.error, "file": file_path}, level='WARNING')

        else:
            self.invalid_files.append()

        # Replace null character with space
        for doc in file_documents:
            doc.page_content = doc.page_content.replace('\x00', ' ')

        return file_documents

    def _error_logger(self, error, action, entity_type) -> None:
        if isinstance(error, str):
            self.logMessage(message={"message": error, "action": action, "entity_type": entity_type}, level='WARNING')
        elif isinstance(error.message, str):
            message_json = json.loads(error.message)
            self.logMessage(message={"message": message_json["errors"][0]["message"], "action": action, "entity_type": entity_type}, level='WARNING')
        else:
            self.logMessage(message={"message": error.message[0]["message"], "action": action, "entity_type": entity_type}, level='WARNING')

    def _load_files_from_folder_path(self, dbx, folder_path) -> List[Document]:
        self.logMessage(message=f"Load files from folder path ({folder_path})", level="DEBUG")

        import dropbox

        file_documents = []

        files = None
        found_all_records = False
        file_paths = []

        try:
            while found_all_records is False:
                if files is None:
                    files = dbx.files_list_folder(
                        folder_path,
                        recursive=True,
                        include_deleted=False,
                    )
                else:
                    files = dbx.files_list_folder_continue(files.cursor)

                for file in files.entries:
                    if isinstance(file, dropbox.files.FileMetadata):
                        file_extension = pathlib.Path(file.name).suffix.replace('.', '')

                        if file_extension in ALLOWED_EXTENSIONS:
                            file_paths.append(file.path_display)

                        else:
                            self.invalid_files.append(file.path_display)

                if files.has_more is False:
                    found_all_records = True

            file_documents = self._load_files_from_paths(
                dbx=dbx,
                file_paths=file_paths
            )
        except dropbox.exceptions.DropboxException as error:
            self.errors.append({"message": error.error, "folder": folder_path})

        return file_documents

    def _load_files_from_paths(self, dbx, file_paths) -> List[Document]:
        self.logMessage(message=f"Load files from file paths (count: {len(file_paths)})", level="DEBUG")

        file_documents = []

        for file_path in file_paths:
            file_documents = file_documents + self._load_file(
                dbx=dbx,
                file_path=file_path
            )

        return file_documents

    def logMessage(self, message, level):
        if level == 'INFO':
            logger.info(message)
        if level == 'DEBUG':
            logger.debug(message)
        if level == 'WARNING':
            logger.warning(message)

            self.errors.append(LogStatement(
                message=message,
                level=level
            ))

        self.progress.append(LogStatement(
            message=message,
            level=level
        ))

    def list_folders(self, dbx, path_root=None):
        import dropbox
        entries_info = []
        try:
            headers = {"Dropbox-API-Path-Root": path_root} if path_root else {}
            files = None
            found_all_records = False

            while not found_all_records:
                if files is None:
                    files = dbx.files_list_folder("", recursive=False, include_deleted=False, headers=headers)
                else:
                    files = dbx.files_list_folder_continue(files.cursor, headers=headers)

                for entry in files.entries:
                    if isinstance(entry, dropbox.files.FolderMetadata):
                        entries_info.append({
                            "name": entry.name,
                            "path_display": entry.path_display,
                            "parent_shared_folder_id": entry.parent_shared_folder_id if hasattr(entry, 'parent_shared_folder_id') else None
                        })
                if not files.has_more:
                    found_all_records = True

        except dropbox.exceptions.DropboxException as error:
            print(f"DropboxException: {error.error}")
        return entries_info

    def get_folders(self):
        import dropbox
        try:
            with dropbox.Dropbox(oauth2_access_token=self.auth['access_token']) as dbx:
                account_info = dbx.users_get_current_account()
                root_namespace_id = account_info.root_info.root_namespace_id

                root_entries_info = self.list_folders(dbx, json.dumps({
                    ".tag": "namespace_id",
                    "namespace_id": root_namespace_id
                }))

                personal_entries_info = self.list_folders(dbx)

                all_entries_info = root_entries_info + personal_entries_info

                return all_entries_info
        except dropbox.exceptions.DropboxException as error:
            print(f"DropboxException: {error.error}")
            return []

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

        # earlier versions of this library used `access`, but the dropbox api returns `access_token`
        if 'access' in self.auth:
            args = {"oauth2_access_token": self.auth['access']}

        # preferred
        if 'access_token' in self.auth:
            args = {"oauth2_access_token": self.auth['access_token']}

        # If an app_key + secret is specified, pass in refresh token, app_key, app_secret
        if self.app_key is not None and self.app_secret is not None:
            # earlier versions of this library used `refresh`, but the dropbox api returns `refresh_token`
            if 'refresh' in self.auth:
                args['oauth2_refresh_token'] = self.auth['refresh']

            # preferred
            if 'refresh_token' in self.auth:
                args['oauth2_refresh_token'] = self.auth['refresh_token']
            args['app_key'] = self.app_key
            args['app_secret'] = self.app_secret

        # Initialize a new Dropbox object
        try:
            dbx_personal = dropbox.Dropbox(**args)
            account_info = dbx_personal.users_get_current_account()
        except dropbox.exceptions.DropboxException as error:
            self.errors.append({"message": error.error})
            return []

        # Initialize a new Dropbox object for team folders with the appropriate headers
        try:
            headers = {
                "Dropbox-API-Path-Root": json.dumps({
                    ".tag": "namespace_id",
                    "namespace_id": account_info.root_info.root_namespace_id
                })
            }
            dbx_team = dropbox.Dropbox(oauth2_access_token=self.auth['access_token'], headers=headers)
        except dropbox.exceptions.DropboxException as error:
            self.errors.append({"message": error.error})
            return []

        # Use the appropriate Dropbox client based on the folder type
        dbx = dbx_team if self.is_team_folder else dbx_personal

        try:
            if self.folder_path is not None:
                return self._load_files_from_folder_path(
                    dbx=dbx,
                    folder_path=self.folder_path
                )

            if self.file_paths is not None:
                return self._load_files_from_paths(
                    dbx=dbx,
                    file_paths=self.file_paths
                )

            return self._load_file(
                dbx=dbx,
                file_path=self.file_path
            )
        except dropbox.exceptions.DropboxException as error:
            self.errors.append({"message": error.error})

        return []

    def _filtered_statements_by_level(self, level) -> List:
        return [statement for statement in self.progress if statement.level == level]

    def get_details(self, level='INFO') -> List:
        if level == 'INFO':
            return self._filtered_statements_by_level(level), self.errors
        return self.progress, self.errors
