"""Echo voice agent for the Voice MVP (S033).

The echo agent simply repeats whatever the user said. Useful for
validating the audio-in -> ASR -> agent -> TTS -> audio-out loop
without depending on a real LLM.
"""

from __future__ import annotations

from loop_voice.session import AgentResponder


def make_echo_agent(*, prefix: str = "You said: ") -> AgentResponder:
    """Build an :data:`AgentResponder` that echoes the user's text.

    The optional ``prefix`` makes echoes auditorily distinguishable
    from the user's own audio when looped through TTS.
    """

    async def _echo(user_text: str) -> str:
        return f"{prefix}{user_text}"

    return _echo


__all__ = ["make_echo_agent"]
