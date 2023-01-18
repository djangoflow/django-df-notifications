from df_notifications.channels import BaseChannel


class TestChannel(BaseChannel):
    key = "test"
    template_parts = ["msg"]
    title_part = "msg"
    additional_data = []
    config_items = []

    def send(self, users, context):
        print(context)
