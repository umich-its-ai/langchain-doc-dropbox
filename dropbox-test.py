from dropbox_files import DropboxLoader

auth = {
	"access": "ACCESS_TOKEN_FROM_OAUTH",
	"refresh": "REFRESH_TOKEN",
	"id_token": "ID_TOKEN_NOT_USED",
	"expire": "EXPIRE_TIMESTAMP"
}

loader = DropboxLoader(
	auth = auth,
	folder_path = "",
	# file_path = "/Canvas Test Files/Sheets Test - Old.xls",
	# file_paths = [
	# 	"/Canvas Test Files/Sheets Test - Old.xls",
	# 	"/Canvas Test Files/Index-me.docx"
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