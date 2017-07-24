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
            glass_name = "_".join(id_and_color)
            self.exist_glasses.append(glass_name)

    def isExist(self, product_id, color_no):
        glass_name = "_".join([product_id, color_no])
        return glass_name in self.exist_glasses