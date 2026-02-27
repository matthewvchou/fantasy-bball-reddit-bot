import azure.functions as func
import logging
import sys
import os

app = func.FunctionApp()

@app.timer_trigger(
    schedule="0 0 7 * * *",  # 7 AM UTC = 2 AM EST (adjust for daylight saving)
    arg_name="myTimer",
    run_on_startup=False,
)
def post_daily(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.warning("Timer is past due — running now.")

    logging.info("Starting daily top ten post...")

    from src.bot.daily.daily_top_ten import main
    main()

    logging.info("Daily top ten post completed.")
