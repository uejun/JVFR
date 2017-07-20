import unittest
import jins
from jins import DynamoClient

class TestCynamoClient(unittest.TestCase):
    def test_get_products(self):
        dynamo_client = DynamoClient()
        items = dynamo_client.get_products()
        print(items)

class TestMisc(unittest.TestCase):
    def test_create_filename(self):
        dir_name1 = "/Users/jins/Desktop"
        dir_name2 = "/Users/jins/Desktop/"
        product_id = "MCF-15S-074"
        color_no = "6"
        angle_id = -3
        fname = jins.create_filename(dir_name1, product_id, color_no, angle_id)
        print(fname)

if __name__ == '__main__':
    unittest.main()