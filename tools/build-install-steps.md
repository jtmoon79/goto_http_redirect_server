## Reminder of steps for building a release

### locally

1. commit bump version `A.B.C`

       git add .
       git commit -m 'bump version A.B.C'
       git push -v

   - wait for CI to complete

2. build release using `build-install` script.

3. upload to pypi following `build-install` script instructions

4. tagging

   new tag `A.B.C`, reset tag `latest`

       git tag -d latest
       git push github :refs/tags/latest
       git tag A.B.C
       git tag latest

5. push tags

       git push -v --tags 

### github.com

1. From _Tags_ page, for `A.B.C` click `...`, select _Create release_.
2. _Release title_ `A.B.C`
3. drag+drop `projct/dist/goto_http_redirect_server-A.B.C-py3-none-any.whl` in
   _Attach binaries_.
4. click _Publish release_
