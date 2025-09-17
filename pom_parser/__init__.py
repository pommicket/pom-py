import io

class Configuration:
	pass

class Settings:
	pass

def load_file(filename: str, file: io.IOBase, settings: Settings = Settings()) -> Configuration:
	raise NotImplementedError('not implemented')

def load_string(filename: str, string: str, settings: Settings = Settings()) -> Configuration:
	return load_file(filename, io.BytesIO(string.encode()), settings)

def load_path(path: str, settings: Settings = Settings()) -> Configuration:
	with open(path, 'rb') as file:
		return load_file(path, file, settings)
