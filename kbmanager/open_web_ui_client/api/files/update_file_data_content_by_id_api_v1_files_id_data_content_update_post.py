from http import HTTPStatus
from typing import Any, Optional, Union, Dict

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.content_form import ContentForm
from ...models.http_validation_error import HTTPValidationError
from ...types import Response
from ...models.file_model import FileModel


def _get_kwargs(
    id: str,
    *,
    body: ContentForm,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "POST",
        "url": "/api/v1/files/{id}/data/content/update".format(
            id=id,
        ),
    }

    _kwargs["json"] = body.to_dict()

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, HTTPValidationError]]:
    if response.status_code == 200:
        response_200 = response.json()
        return response_200
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[Any, HTTPValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    id: str,
    *,
    client: AuthenticatedClient,
    body: ContentForm,
) -> Response[Union[Any, HTTPValidationError]]:
    """Update File Data Content By Id

    Args:
        id (str):
        body (ContentForm):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        id=id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    id: str,
    *,
    client: AuthenticatedClient,
    body: ContentForm,
) -> Optional[Union[Any, HTTPValidationError]]:
    """Update File Data Content By Id

    Args:
        id (str):
        body (ContentForm):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, HTTPValidationError]
    """

    return sync_detailed(
        id=id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    id: str,
    *,
    client: AuthenticatedClient,
    body: ContentForm,
) -> Response[Union[Any, HTTPValidationError]]:
    """Update File Data Content By Id

    Args:
        id (str):
        body (ContentForm):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        id=id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    id: str,
    *,
    client: AuthenticatedClient,
    body: ContentForm,
) -> Optional[Union[Any, HTTPValidationError]]:
    """Update File Data Content By Id

    Args:
        id (str):
        body (ContentForm):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            id=id,
            client=client,
            body=body,
        )
    ).parsed
