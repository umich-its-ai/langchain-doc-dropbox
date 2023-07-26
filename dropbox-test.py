from dropbox_files import DropboxLoader

loader = DropboxLoader(
	token = "TOKEN_GOES_HERE",
	folder_path = "/PATH_TO_FOLDER_OR_EMPTY_STRING"
	# file_path = "/PATH/TO_FILE/File.extension"
	# file_paths = [
	# 	"/PATH/TO_FILE/File 1.extension",
	# 	"/PATH/TO_FILE/File 2.extension"
	# ]
)

documents = loader.load()

print("\nDocuments:\n")
print(documents)

print("\nInvalid files:\n")
print(loader.invalid_files)
print("")