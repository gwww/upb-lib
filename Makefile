.PHONY: install clean isort lint debug test

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '.cache' -exec rm -rf {} +
	find . -name '.pytest_cache' -exec rm -rf {} +
	rm -rf build dist *.egg-info

install:
	poetry install

build:
	poetry build

upload.test: build
	poetry publish --repository test

upload: build
	poetry publish

isort:
	sh -c "isort --skip-glob=.tox --recursive . "

lint:
	pylint --msg-template='{msg_id}({symbol}):{line:3d},{column}: {obj}: {msg}' upb_lib

run:
	bin/TBD

test:
	pytest
