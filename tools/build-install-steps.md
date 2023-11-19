## Create A New Release

A reminder of end-to-end steps for creating a new release.

### locally

1. modify `__version__` string to `A.B.C`

2. run `goto_http_redirect_server.py --help`<br />
   update the top-level `README.md` with the latest `--help`

3. commit bump version `A.B.C` and updated `--help`

       git add .
       git commit -m 'bump version A.B.C'
       git push -v

   - wait for CI to complete

4. build release using `build-install` script.

5. upload to pypi following `build-install` script instructions<br/>
   or
   ```text
   python -m twine upload --username "__token__" --verbose ./dist/goto_http_redirect_server-A.B.C-py3-none-any.whl
   ```
   Create an upload token at [pypi.org/manage/account/token/](https://pypi.org/manage/account/token/).

6. tagging

   new tag `A.B.C`, reset tag `latest`

       git tag -d latest
       git push github :refs/tags/latest
       git tag A.B.C
       git tag latest

7. push tags

       git push -v --tags

### github.com

1. From _Tags_ page, for `A.B.C` click `...`, select _Create release_.
2. _Release title_ `A.B.C`.
3. drag+drop `projct/dist/goto_http_redirect_server-A.B.C-py3-none-any.whl` in
   _Attach binaries_.
4. add pypi URL with version in _Write_ area.
5. click _Publish release_.

## update local server

On server running `goto_http_redirect_server`

1. pip upgrade
   ```bash
   pip install --upgrade goto-http-redirect-server
   ```

2. restart service
   ```bash
   systemctl restart goto_http_redirect_server.service
   ```
   **TODO:** this step should reference wheel package `systemd_install`.

3. check status
   ```bash
   systemctl status goto_http_redirect_server.service
   journalctl -u goto_http_redirect_server.service
   cat /var/log/goto_http_redirect_server.log
   ```
   Sometimes the tcp socket remains open and prevents new instances. Close all
   browser windows viewing `--status-path`.

4. web browser to `--status-path` locally
