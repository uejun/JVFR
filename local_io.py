import glob


class FileChecker:
    def __init__(self, save_dir: str):
        if save_dir[-1] != '/':
            save_dir += '/'

        filenames = glob.glob(save_dir + '*.png')

        self.exist_glasses = []

        for filename in filenames:
            object_name = filename.split('/')[-1]
            id_and_color = object_name.split('_')[0:2]
            print(id_and_color)
            self.exist_glasses.append((id_and_color))


def isExist():
    pass