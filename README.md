# Canvas langchain document loader

Features:

Indexes Dropbox Files

The following file types are supported:
  `md` `htm` `html` `docx` `xls` `xlsx` `pptx` `pdf` `rtf` `txt`

(`doc` support would require libreoffice, so has not been implemented in this library)

## Running locally

You can do the install as described below, or build/run the provider dockerfile.

## Docker

Edit dropbox-test.py, fill in the correct `auth` and one of `folder_path`, `file_path`, or `file_paths`.

Run (this also builds docker):

```bash
docker run -it $(docker build -q .)
```

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage example:

To use a refresh token, pass in `api_key` along with `api_secret`

```python
from dropbox_files import DropboxLoader

auth = {
  "access": "ACCESS_TOKEN_FROM_OAUTH",
  "refresh": "REFRESH_TOKEN",
  "id_token": "ID_TOKEN_NOT_USED",
  "expire": "EXPIRE_TIMESTAMP"
}

loader = DropboxLoader(
	auth = auth,
	folder_path = "/PATH_TO_FOLDER_OR_EMPTY_STRING",
	# file_path = "/PATH/TO_FILE/File.extension",
	# file_paths = [
	# 	"/PATH/TO_FILE/File 1.extension",
	# 	"/PATH/TO_FILE/File 2.extension"
	# ],
	# api_key = "API_KEY",
	# api_secret = "API_SECRET",
)

documents = loader.load()

print("\nDocuments:\n")
print(documents)

print("\nInvalid files:\n")
print(loader.invalid_files)
print("")

print("\nErrors:\n")
print(loader.errors)
print("")
```

If errors are present, `loader.errors` will contain one list element per error. It will consist of an error message (key named `message`) and if the error pertains to a folder issue, a key named `folder`, for files a `file` key. Right now the library only catches Dropbox API specific exceptions.
