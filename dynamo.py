import boto3
from jins_entity import GlassProduct


class DynamoClient:

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')
        self.table = self.dynamodb.Table("jvfr_glass")
        self.color_table = self.dynamodb.Table("jvfr_color")
        if self.table == None:
            raise Exception("table is None.")


    def put_product(self, product: GlassProduct, page_num: int):
        response = self.table.put_item(
            Item={
                'ProductID': product.product_id,
                'PageNum': page_num,
                'Colors': product.color_list
            }
        )

    def put_products(self, products, page_num: int):
        for product in products:
            self.put_product(product, page_num)

    def get_products(self):
        res = self.table.scan()
        print("Items: " + str(len(res["Items"])))
        return res["Items"]

    def put_color(self, color_id, color_name):
        response = self.color_table.put_item(
            Item={
                'color_id': color_id,
                'color_name': color_name
            }
        )

