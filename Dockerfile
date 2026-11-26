FROM python:3.13-slim

WORKDIR /app
COPY notifier ./notifier
COPY bot.py entrypoint.sh ./

RUN useradd --create-home --uid 1000 bot \
    && mkdir -p /app/data \
    && chown bot:bot /app/data \
    && chmod 755 /app/entrypoint.sh \
    && command -v setpriv >/dev/null

ENV PYTHONUNBUFFERED=1

EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-u", "bot.py"]
