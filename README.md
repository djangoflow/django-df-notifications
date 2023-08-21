# Djangoflow Omnichannel Notifications

Opinionated Django Omnichannel Notifications


## Principles

* **Opinionated:** Create a set of strict guidelines to be followed by the users
  and developers. Well defined and consistent guidelines reduces errors and
  unwanted side-effects. Framework should be easy to understand, implement and maintain.

* **Secure:** Follow the industry best practices secure software development; communications;
  storage as well as long term maintenance. Always evaluate the risk and trade-offs in
  appropriate contexts.

* **Clean code:** Strictly follow DRY principle; write your code for other developers
  to understand; document and keep documentation updated; automate testing your code,
  packaging, deployments and other processes; discuss your ideas before implementing unless
  you are absolutely sure; be a good craftsmen.

* **Open:** Offer source code and related artifacts under open source licenses. Build
  and manage a collaborative community where everyone is welcome.

* **Configurable:** Provide ways to change behavior, appearance and offer extension points
  everywhere possible.

* **Reuse:** Do not reinvent the wheel. Use existing high-quality modules as much as possible.

## Endpoints

* `devices/`
* `action-categories/`

## Data model

...

## Views and templates

...


## Development


### Running test application.

Here you can check admin and API endpoints.

```
python3 -m venv venv
. venv/bin/activate
pip install -e .[test]
./manage.py runserver
```


### Running tests

```
# Without coverage report
make test

# With coverage report
make test-cov
```


### Deploying new version

Change version in `setup.cfg` and push new tag to main branch.

```
git tag 0.0.x
git push --tags
```

## Other modules and links out there


...

## Sponsors


[Apexive OSS](https://apexive.com)
