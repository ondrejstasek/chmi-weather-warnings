"""Config flow for ČHMI integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ID
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN #,CONST_DISABLEAUTOPOLL


class CHMIFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CHMI."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> CHMIOptionFlowHandler:
        """Get the options flow for this handler."""
        return CHMIOptionFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        if user_input is not None:
            return self.async_create_entry(
                title= "ČHMÚ", 
                data = {},
                options={
                    CONF_ID: user_input[CONF_ID],
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ID, default=""): str,
                }
            ),
        )


class CHMIOptionFlowHandler(OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="ČHMÚ", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ID,
                        default=self.config_entry.options.get(CONF_ID),
                    ): str,
                }
            ),
        )
