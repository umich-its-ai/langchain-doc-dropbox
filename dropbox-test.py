from dropbox_langchain.dropbox_files import DropboxLoader

auth = {
	"access_token": "ACCESS_TOKEN_FROM_OAUTH",
	"refresh_token": "REFRESH_TOKEN",
	"expires_at": "EXPIRE_TIMESTAMP"
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

print("\nErrors:\n")
print(loader.errors)
print("")