"""Stream mp3 cua TTS Blaze da mo san: status da kiem, chunk dau da doc.

Loi truoc byte dau (status loi, khong co du lieu, mat ket noi) duoc nem thanh ApiError de route tra JSON; sau khi route
tra StreamingResponse thi loi giua chung chi dong stream (contract). Route dong response qua BackgroundTask(aclose).
"""
from typing import AsyncIterator

import httpx

from .api_error import ApiError


class SpeechStream:
    def __init__(self, response: httpx.Response, chunks: AsyncIterator[bytes], first_chunk: bytes):
        """Dung SpeechStream.open(response), khong goi truc tiep."""
        self._response = response
        self._chunks = chunks
        self._first = first_chunk

    @classmethod
    async def open(cls, response: httpx.Response) -> "SpeechStream":
        """Doc chunk khong rong dau tien; response duoc dong neu that bai."""
        chunks = response.aiter_bytes()
        try:
            first = b""
            while not first:  # bo chunk rong; None = stream het ma chua co byte nao
                first = await anext(chunks, None)
                if first is None:
                    break
        except httpx.TimeoutException:
            await response.aclose()
            raise ApiError(504, "provider_timeout", "Nhà cung cấp giọng nói không trả âm thanh kịp thời") from None
        except httpx.HTTPError:
            await response.aclose()
            raise ApiError(502, "provider_error", "Mất kết nối tới nhà cung cấp giọng nói") from None
        if not first:
            await response.aclose()
            raise ApiError(502, "provider_error", "Nhà cung cấp giọng nói không trả âm thanh")
        return cls(response, chunks, first)

    async def __aiter__(self) -> AsyncIterator[bytes]:
        try:
            yield self._first
            async for chunk in self._chunks:
                if chunk:
                    yield chunk
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        await self._response.aclose()
