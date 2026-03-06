from __future__ import annotations

from enum import Enum


class Feature(str, Enum):
    # Posting
    POST_PHOTO = "post_photo"
    POST_VIDEO = "post_video"
    POST_REEL = "post_reel"
    POST_CAROUSEL = "post_carousel"
    # DMs
    DM_INBOX = "dm_inbox"
    DM_PENDING = "dm_pending"
    DM_THREAD = "dm_thread"
    DM_REPLY = "dm_reply"
    DM_COLD_SEND = "dm_cold_send"
    DM_SEND_MEDIA = "dm_send_media"
    DM_SEARCH = "dm_search"
    DM_DELETE = "dm_delete"
    DM_MUTE = "dm_mute"
    DM_LISTEN = "dm_listen"
    # Stories
    STORY_LIST = "story_list"
    STORY_POST = "story_post"
    STORY_VIEW_OTHERS = "story_view_others"
    STORY_VIEWERS = "story_viewers"
    # Comments
    COMMENTS_LIST = "comments_list"
    COMMENTS_REPLY = "comments_reply"
    COMMENTS_DELETE = "comments_delete"
    # Analytics
    ANALYTICS_PROFILE = "analytics_profile"
    ANALYTICS_POST = "analytics_post"
    ANALYTICS_HASHTAG = "analytics_hashtag"
    # Followers
    FOLLOWERS_LIST = "followers_list"
    FOLLOWERS_FOLLOWING = "followers_following"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    # User
    USER_INFO = "user_info"
    USER_SEARCH = "user_search"
    USER_POSTS = "user_posts"
    # Engagement
    LIKE_POST = "like_post"
    UNLIKE_POST = "unlike_post"
    COMMENTS_ADD = "comments_add"
    # Hashtag browsing
    HASHTAG_TOP = "hashtag_top"
    HASHTAG_RECENT = "hashtag_recent"


CAPABILITY_MATRIX: dict[str, set[Feature]] = {
    "graph_ig": {
        Feature.POST_PHOTO, Feature.POST_VIDEO, Feature.POST_REEL, Feature.POST_CAROUSEL,
        Feature.COMMENTS_LIST, Feature.COMMENTS_REPLY, Feature.COMMENTS_DELETE,
        Feature.COMMENTS_ADD,
        Feature.ANALYTICS_PROFILE, Feature.ANALYTICS_POST, Feature.ANALYTICS_HASHTAG,
        Feature.HASHTAG_TOP, Feature.HASHTAG_RECENT,
        Feature.USER_INFO, Feature.USER_SEARCH,
    },
    "graph_fb": {
        Feature.POST_PHOTO, Feature.POST_VIDEO, Feature.POST_REEL, Feature.POST_CAROUSEL,
        Feature.DM_INBOX, Feature.DM_THREAD, Feature.DM_REPLY, Feature.DM_SEND_MEDIA,
        Feature.DM_LISTEN,
        Feature.STORY_POST,
        Feature.COMMENTS_LIST, Feature.COMMENTS_REPLY, Feature.COMMENTS_DELETE,
        Feature.COMMENTS_ADD,
        Feature.ANALYTICS_PROFILE, Feature.ANALYTICS_POST, Feature.ANALYTICS_HASHTAG,
        Feature.HASHTAG_TOP, Feature.HASHTAG_RECENT,
        Feature.USER_INFO, Feature.USER_SEARCH,
    },
    "private": set(Feature),
}

READ_ONLY_FEATURES: set[Feature] = {
    Feature.DM_INBOX, Feature.DM_PENDING, Feature.DM_THREAD, Feature.DM_SEARCH,
    Feature.DM_LISTEN,
    Feature.STORY_LIST, Feature.STORY_VIEW_OTHERS, Feature.STORY_VIEWERS,
    Feature.COMMENTS_LIST,
    Feature.ANALYTICS_PROFILE, Feature.ANALYTICS_POST, Feature.ANALYTICS_HASHTAG,
    Feature.FOLLOWERS_LIST, Feature.FOLLOWERS_FOLLOWING,
    Feature.USER_INFO, Feature.USER_SEARCH, Feature.USER_POSTS,
    Feature.HASHTAG_TOP, Feature.HASHTAG_RECENT,
}

GROWTH_ACTIONS: set[Feature] = {
    Feature.FOLLOW, Feature.UNFOLLOW,
    Feature.LIKE_POST, Feature.UNLIKE_POST, Feature.COMMENTS_ADD
}


def can_backend_do(backend: str, feature: Feature) -> bool:
    caps = CAPABILITY_MATRIX.get(backend, set())
    return feature in caps
