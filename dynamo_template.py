from dynamo import DynamoClient
dc = DynamoClient()

dc.put_glass("sample_id", "http://localhost/", [{"id":33, "name":"yellow"}, {"id":39, "name":"black"}])