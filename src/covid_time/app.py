"""COVID Time — a clock stuck in March 2020."""
import asyncio

import toga
from toga.style import Pack

from .clock import covid_time_string, day_number


class CovidTimeApp(toga.App):
    def startup(self):
        self.day_label = toga.Label(
            f"Day {day_number()}",
            style=Pack(font_size=56, font_weight="bold", text_align="center"),
        )
        self.subtitle_label = toga.Label(
            "of March 2020",
            style=Pack(font_size=16, text_align="center"),
        )
        self.time_label = toga.Label(
            covid_time_string(),
            style=Pack(
                font_size=18,
                font_family="monospace",
                text_align="center",
                margin_top=24,
            ),
        )
        main_box = toga.Box(
            children=[self.day_label, self.subtitle_label, self.time_label],
            style=Pack(
                direction="column",
                align_items="center",
                justify_content="center",
            ),
        )
        self.main_window = toga.MainWindow(size=(360, 240), resizable=False)
        self.main_window.content = main_box
        self.main_window.show()

    def _refresh(self):
        self.day_label.text = f"Day {day_number()}"
        self.time_label.text = covid_time_string()

    async def on_running(self):
        # Fires once the event loop is up. Each await yields control back to
        # the loop, so the UI stays responsive while the clock ticks.
        while True:
            self._refresh()
            await asyncio.sleep(1)


def main():
    return CovidTimeApp(
        formal_name="COVID Time",
        app_id="com.kattni.covidtime",
    )
