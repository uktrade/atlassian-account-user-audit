FROM public.ecr.aws/docker/library/python:3.10-buster

RUN pip install poetry==1.0.0

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install

COPY cleanup_atlassian.py ./

CMD run.sh