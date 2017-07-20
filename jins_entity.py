class GlassProduct:

    def __init__(self, product_id: str):
        self.product_id: str = product_id
        self.color_list: list[str] = []

    def add_color(self, color_id: str):
        self.color_list.append(color_id)

    def create_detail_page_href(self, color_id):
        return "https://www.jins.com/jp/Products/Detail/number/" + self.product_id + "/" + color_id + "/?from_search=1"

