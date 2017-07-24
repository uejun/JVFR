import unittest
import local_io


class TestFileChecker(unittest.TestCase):

    def test_create_filechecker(self):
        save_dir = 'sample/images/'
        local_io.FileChecker(save_dir)



if __name__ == '__main__':
    unittest.main()