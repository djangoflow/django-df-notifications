import json
import unittest
from typing import List
from unittest.mock import MagicMock

import requests_mock

from df_notifications.channels import JSONPostWebhookChannel


class TestJSONPostWebhookChannel(unittest.TestCase):

    def setUp(self):
        self.channel = JSONPostWebhookChannel()
        self.users: List[MagicMock] = [MagicMock()]
        self.base_context = {
            "subject.txt": "https://example.com/webhook",
            "body.txt": "Dummy message",
            "data.json": '{"key": "value"}',
        }

    def _run_send_with_context(self, context, exception):
        with self.assertRaises(exception):
            self.channel.send(self.users, context)

    def test_send_with_missing_subject_txt_key(self):
        context = self.base_context.copy()
        del context["subject.txt"]
        self._run_send_with_context(context, KeyError)

    def test_send_with_missing_body_txt_key(self):
        context = self.base_context.copy()
        del context["body.txt"]
        self._run_send_with_context(context, KeyError)

    def test_send_with_missing_data_json_key(self):
        context = self.base_context.copy()
        del context["data.json"]
        self._run_send_with_context(context, KeyError)

    def test_send_with_invalid_data_json(self):
        context = self.base_context.copy()
        context["data.json"] = '{INVALID_JSON}'
        self._run_send_with_context(context, json.JSONDecodeError)

    @requests_mock.Mocker()
    def test_send_with_empty_body_txt(self, req_mock):
        req_mock.post("https://example.com/webhook", status_code=200)
        context = self.base_context.copy()
        context["body.txt"] = ""
        self.channel.send(self.users, context)
        assert req_mock.called
        assert req_mock.call_count == 1
        assert req_mock.last_request.url == "https://example.com/webhook"
        assert req_mock.last_request.json() == {"key": "value"}

    @requests_mock.Mocker()
    def test_send_with_empty_data_json(self, req_mock):
        req_mock.post("https://example.com/webhook", status_code=200)
        context = self.base_context.copy()
        context["data.json"] = '{}'
        self.channel.send(self.users, context)
        assert req_mock.called
        assert req_mock.call_count == 1
        assert req_mock.last_request.url == "https://example.com/webhook"
        assert req_mock.last_request.text == "Dummy message"
