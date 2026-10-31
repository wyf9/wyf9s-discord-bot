import unittest
from unittest import mock

import discord

import utils as u


def _acknowledged_error() -> discord.HTTPException:
    response = mock.Mock()
    response.status = 400
    response.reason = "Bad Request"
    return discord.HTTPException(
        response,
        {"message": "Interaction has already been acknowledged.", "code": 40060},
    )


class SendMsgTest(unittest.IsolatedAsyncioTestCase):
    async def test_stale_interaction_response_falls_back_to_followup(self):
        interaction = mock.Mock(spec=discord.Interaction)
        interaction.response.is_done.return_value = False
        interaction.response.send_message = mock.AsyncMock(
            side_effect=_acknowledged_error()
        )
        interaction.followup.send = mock.AsyncMock(return_value=None)

        await u.send_msg(interaction, "hello", ephemeral=True)

        interaction.followup.send.assert_awaited_once()
        call = interaction.followup.send.await_args
        assert call is not None
        self.assertEqual(call.args[0], "hello")

    async def test_stale_followup_is_ignored(self):
        interaction = mock.Mock(spec=discord.Interaction)
        interaction.response.is_done.return_value = True
        interaction.followup.send = mock.AsyncMock(side_effect=_acknowledged_error())

        result = await u.send_msg(interaction, "hello", ephemeral=True)

        self.assertIsNone(result)

    async def test_other_http_errors_are_raised(self):
        interaction = mock.Mock(spec=discord.Interaction)
        interaction.response.is_done.return_value = True
        response = mock.Mock()
        response.status = 500
        response.reason = "Internal Server Error"
        error = discord.HTTPException(response, {"message": "boom", "code": 0})
        interaction.followup.send = mock.AsyncMock(side_effect=error)

        with self.assertRaises(discord.HTTPException):
            await u.send_msg(interaction, "hello")


if __name__ == "__main__":
    unittest.main()
