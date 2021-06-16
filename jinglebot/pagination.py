import asyncio
from asyncio import AbstractEventLoop, get_event_loop, Task
from typing import List, Callable, Optional, Union, Tuple, Iterable

from discord import TextChannel, Message, Client, Reaction, User, Member

from jinglebot.emojis import UnicodeEmoji

ON_REACTION_ADD_CALLABLE = Callable[[Reaction, Union[Member, User]], bool]


def combine_predicates(*predicates: Callable[..., bool]) -> Callable[..., bool]:
    """
    Combine multiple predicates into a single one. The result is true only if all of the predicates are satisfied.
    """

    def check_all(*args, **kwargs) -> bool:
        return all(map(lambda f: f(*args, **kwargs), predicates))

    return check_all


def is_message_author(author_id: int) -> Callable[[Message], bool]:
    """
    Higher order function, returns the callback that will receive a Message and check if the authors match.
    :param author_id: Message author ID.
    :return: Callable that expects to receive a Message and
    return a boolean indicating whether the author is as specified.
    """

    def check(m: Message) -> bool:
        return m.author.id == author_id

    return check


def is_reaction_author(author_id: int) -> ON_REACTION_ADD_CALLABLE:
    """
    Higher order function, returns the callback that will receive a Reaction and a User and check if the authors match.
    :param author_id: Message author ID.
    :return: Callable that expects to receive a Message and
    return a boolean indicating whether the author is as specified.
    """

    def check(_: Reaction, u: Union[Member, User]) -> bool:
        return u.id == author_id

    return check


def is_reaction_emoji(emoji_list: Iterable[str]) -> ON_REACTION_ADD_CALLABLE:
    """
    Higher order function, returns the callback that will receive a Reaction and a User and check if the emoji matches.
    :param emoji_list: A list of emojis to expect.
    :return: Callable that expects to receive a Message and
    return a boolean indicating whether the author is as specified.
    """

    def check(r: Reaction, _: Union[Member, User]) -> bool:
        return r.emoji in emoji_list

    return check


class Pagination:
    """
    A broad implementation of the pagination logic for Discord.
    Handles sending the initial message and acting on pagination actions.

    Instances of Pagination are awaitable, and will complete when the pagination is done (timed out / stopped manually).
    """
    def __init__(
        self, *,

        # Channel and client options
        channel: TextChannel,
        client: Client,
        loop: AbstractEventLoop = get_event_loop(),

        # Content options
        beginning_content: str = "",
        item_list: List[str],
        item_max_per_page: int,
        end_content: str = "",

        # Additional content options
        item_separator: str = "\n",
        code_block_begin: str = "```\n",
        code_block_end: str = "```",
        message_length_limit: int = 1990,

        # Pagination options
        paginate_action_check: ON_REACTION_ADD_CALLABLE,
        pagination_emojis: Tuple[str, str, str] = (
            UnicodeEmoji.ARROW_BACKWARD,
            UnicodeEmoji.ARROW_FORWARD,
            UnicodeEmoji.STOP_BUTTON
        ),

        # Timeout options
        timeout: int = 240,
        timeout_message: Optional[str] = None,

        # Misc options
        begin_pagination_immediately: bool = True,
    ):
        """
        A generic Discord pagination method. Completes when timed out or when the user manually stops pagination.

        :param beginning_content: Content to be placed before the list of items on the current page.
        :param item_list: A list of strings representing individual items.
        :param item_separator: Defaults to a newline. This will be placed between each item.
        :param item_max_per_page: The maximum amount of items to be shown on each page.
        :param end_content: Content to be placed after the list of items.
        :param paginate_action_check: A callable that will handle the on_reaction_add event and
        return a boolean - this function will act as an additional filter for the pagination.
        :param channel: TextChannel to paginate in.
        :param client: Client/Bot to use.
        :param timeout: How long to wait between each interaction. If timed out, (optionally) send the timeout message.
        :param timeout_message: Optionally, a message to be sent after timing out.
        :param code_block_begin: Defaults to "```\n".
        :param code_block_end: Defaults to "```"
        :param message_length_limit: Defaults to 1990. This limits the length of the entire message.
        :param pagination_emojis: A tuple containing three emojis to be used
        for pagination: previous page, next page and stop emoji.
        :param begin_pagination_immediately: Whether to immediately begin pagination
        (sends the message into the specified channel).
        """
        self.is_running: bool = False
        self.pagination_message: Optional[Message] = None
        self.pagination_task: Optional[Task] = None

        self.channel: TextChannel = channel
        self.client: Client = client
        self.loop: AbstractEventLoop = loop

        self.content_beginning: str = beginning_content
        self.item_list: List[str] = item_list
        self.item_max_per_page: int = item_max_per_page
        self.content_end: str = end_content

        self.item_separator: str = item_separator
        self.code_block_begin: str = code_block_begin
        self.code_block_end: str = code_block_end
        self.message_length_limit: int = message_length_limit

        self.paginate_action_check: ON_REACTION_ADD_CALLABLE = paginate_action_check
        self.pagination_emojis: Tuple[str, str, str] = pagination_emojis

        self.timeout: int = timeout
        self.timeout_message: Optional[str] = timeout_message

        if begin_pagination_immediately:
            self.pagination_task = self.loop.create_task(self.begin_pagination())

    def __await__(self):
        return self.pagination_task.__await__()

    #####
    # Helper methods
    #####
    def _render_pagination_message(self, pages: List[str], page_index: int) -> str:
        """
        Form a complete message using the page_number
        """
        return \
            self.content_beginning \
            + self.code_block_begin \
            + pages[page_index] \
            + self.code_block_end \
            + self.content_end

    async def _recreate_pagination_actions(self, m: Message, page_index: int, page_total: int):
        """
        Clear reactions and add any necessary left/right arrows as well as the stop button.
        """
        await m.clear_reactions()

        emoji_page_back, emoji_page_forward, emoji_stop = self.pagination_emojis

        if page_index > 0:
            await m.add_reaction(emoji_page_back)
        if page_index < (page_total - 1):
            await m.add_reaction(emoji_page_forward)
        await m.add_reaction(emoji_stop)

    #####
    # Public methods
    #####
    async def begin_pagination(self):
        if self.is_running:
            return
        self.is_running = True

        # How much space is left for items on each page
        chars_left_for_items = \
            self.message_length_limit \
            - len(self.content_beginning) \
            - len(self.content_end) \
            - len(self.code_block_begin) \
            - len(self.code_block_end)

        emoji_page_back, emoji_page_forward, emoji_stop = self.pagination_emojis

        pages: List[str] = []
        items_per_page: List[int] = []

        # Generate pages from item_list
        for item in self.item_list:
            # If no pages, create one with the item
            if len(pages) < 1:
                pages.append(item)
                items_per_page.append(1)
                continue

            last_page = pages[-1]
            items_in_last_page = items_per_page[-1]

            # If last page has space, add the item to it
            if \
                (len(last_page) + len(self.item_separator) + len(item)) < chars_left_for_items \
                    and (items_in_last_page + 1) <= self.item_max_per_page:
                pages[-1] += self.item_separator + item
                items_per_page[-1] += 1

            # Otherwise create a new page for the item
            else:
                pages.append(item)
                items_per_page.append(1)

        page_current = 0
        page_total = len(pages)

        # Send the initial message
        self.pagination_message: Message = await self.channel.send(self._render_pagination_message(pages, page_current))

        # Continue monitoring for pagination requests until exited or timed out
        while self.is_running:
            await self._recreate_pagination_actions(self.pagination_message, page_current, page_total)

            # Create a function that will check whether the correct emoji
            # was added as well as check for any additional stuff the user wants
            final_pagination_checker = combine_predicates(
                self.paginate_action_check,
                is_reaction_emoji(self.pagination_emojis),
            )

            try:
                reaction, user = await self.client.wait_for(
                    'reaction_add', timeout=self.timeout, check=final_pagination_checker,
                )
            except asyncio.TimeoutError:
                if self.timeout_message:
                    await self.channel.send(self.timeout_message)
                await self.stop_pagination()
                return

            # Process the pagination request
            reaction: Reaction

            if reaction.emoji == emoji_page_back and page_current > 0:
                page_current -= 1
            elif reaction.emoji == emoji_page_forward and (page_current + 1) < page_total:
                page_current += 1
            elif reaction.emoji == emoji_stop:
                await self.stop_pagination()
                return

            await self.pagination_message.edit(content=self._render_pagination_message(pages, page_current))

    def begin_pagination_non_blocking(self):
        """
        A non-blocking version of `self.paginate`.
        """
        self.pagination_task = self.loop.create_task(self.begin_pagination())

    async def stop_pagination(self, delete_message: bool = False):
        """
        If currently paginating or waiting for input, stop pagination.
        :param delete_message: Whether to delete the pagination message as well. Defaults to False.
        """
        if not self.is_running:
            return
        self.is_running = False

        if delete_message is True:
            await self.pagination_message.delete()
        else:
            await self.pagination_message.clear_reactions()
        self.pagination_message = None

        if self.pagination_task is not None:
            self.pagination_task.cancel()
