"""
Slightly more pythonic bindings to libsecret
"""

__license__ = 'GPL-3.0+'

import asyncio
import gi
gi.require_version('Secret', '1')
from gi.repository import GLib, Secret
import logging
from typing import Awaitable


class SecretService:

    _account_schema = Secret.Schema.new(
        'io.github.Pithos.Account',
        Secret.SchemaFlags.NONE,
        {'Credentials': Secret.SchemaAttributeType.STRING},
    )

    def __init__(self):
        self._current_collection = Secret.COLLECTION_DEFAULT

    def unlock_keyring(self) -> Awaitable:
        future = asyncio.Future()  # type: asyncio.Future

        def on_unlock_finish(source, result, data):
            service, default_collection = data
            try:
                num_items, unlocked = service.unlock_finish(result)
            except GLib.Error as e:
                future.set_exception(e)
            else:
                if not num_items or default_collection not in unlocked:
                    self._current_collection = Secret.COLLECTION_SESSION
                    logging.debug('The default keyring is still locked. Using session collection.')
                else:
                    logging.debug('The default keyring was unlocked.')
                future.set_result(None)

        def on_for_alias_finish(source, result, service):
            try:
                default_collection = Secret.Collection.for_alias_finish(result)
            except GLib.Error as e:
                future.set_exception(e)
            else:
                if default_collection is None:
                    self._current_collection = Secret.COLLECTION_SESSION
                    future.set_result(None)
                elif default_collection.get_locked():
                    logging.debug('The default keyring is locked.')
                    service.unlock([default_collection], None, on_unlock_finish,
                                   (service, default_collection))
                else:
                    logging.debug('The default keyring is unlocked.')
                    future.set_result(None)

        def on_get_finish(source, result, data):
            try:
                service = Secret.Service.get_finish(result)
            except GLib.Error as e:
                future.set_exception(e)
            else:
                Secret.Collection.for_alias(
                    service,
                    Secret.COLLECTION_DEFAULT,
                    Secret.CollectionFlags.NONE,
                    None,
                    on_for_alias_finish,
                    service,
                )

        Secret.Service.get(Secret.ServiceFlags.NONE, None,
                           on_get_finish, None)
        return future

    def get_account_credentials(self, account_name: str) -> Awaitable[str, str]:
        future = asyncio.Future()  # type: asyncio.Future

        def on_password_lookup_finish(source, result, data):
            try:
                creds = Secret.password_lookup_finish(result)
            except GLib.Error as e:
                future.set_exception(e)
            else:
                email, password = creds.split('\n') if creds else ('', '')
                future.set_result(email, password)

        Secret.password_lookup(
            self._account_schema,
            {'Credentials': account_name},
            None,
            on_password_lookup_finish,
            None,
        )
        return future

    def set_account_credentials(self, account_name: str, email: str, password: str) -> Awaitable[bool]:
        # account_name can be totally arbitrary and is only used
        # to differentiate between the sets of Credentials.
        future = asyncio.Future()  # type: asyncio.Future

        def on_password_store_finish(source, result, data):
            try:
                success = Secret.password_store_finish(result)
            except GLib.Error as e:
                future.set_exception(e)
            else:
                future.set_result(success)

        Secret.password_store(
            self._account_schema,
            {'Credentials': account_name},
            self._current_collection,
            'Pandora Account',
            '\n'.join((email, password)),
            None,
            on_password_store_finish,
            None,
        )
        return future

    def remove_account_credentials(self, account_name: str) -> Awaitable[bool]:
        future = asyncio.Future()  # type: asyncio.Future

        def on_password_clear_finish(source, result, data):
            try:
                success = Secret.password_clear_finish(result)
            except GLib.Error as e:
                future.set_exception(e)
            else:
                future.set_result(success)

        Secret.password_clear(
            self._account_schema,
            {'Credentials': account_name},
            None,
            on_password_clear_finish,
            None,
        )
        return future
