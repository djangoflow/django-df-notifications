from .settings import api_settings

import tweepy
from tweepy.errors import NotFound


def connect_api(consumer_key, consumer_secret, access_token, access_token_secret):
    auth = tweepy.Client(consumer_key=consumer_key, consumer_secret=consumer_secret, access_token=access_token,
                         access_token_secret=access_token_secret)
    return auth


def send_dm(text):
    if api_settings.TWITTER_CONSUMER_KEY is None:
        raise ValueError('TWITTER_CONSUMER_KEY is required.')

    if api_settings.TWITTER_CONSUMER_SECRET is None:
        raise ValueError('TWITTER_CONSUMER_SECRET is required.')

    if api_settings.TWITTER_ACCESS_TOKEN is None:
        raise ValueError('TWITTER_ACCESS_TOKEN is required.')

    if api_settings.TWITTER_ACCESS_TOKEN_SECRET is None:
        raise ValueError('TWITTER_ACCESS_TOKEN_SECRET is required.')

    if api_settings.TWITTER_USERNAME is None:
        raise ValueError('TWITTER_USERNAME is required')

    api = connect_api(api_settings.TWITTER_CONSUMER_KEY, api_settings.TWITTER_CONSUMER_SECRET,
                      api_settings.TWITTER_ACCESS_TOKEN, api_settings.TWITTER_ACCESS_TOKEN_SECRET)

    try:
        response = api.get_user(username=api_settings.TWITTER_USERNAME, user_auth=True)
    except NotFound:
        raise ValueError(f'TWITTER_USERNAME {api_settings.TWITTER_USERNAME} does not exist.')

    user_id = response.data.id
    api.create_direct_message(text=text, participant_id=user_id)
