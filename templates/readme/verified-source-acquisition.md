Build the verified repository revision from source:

```bash
git clone https://github.com/{org_repo}.git
cd {repository_name}
git checkout {source_revision}
mvn clean install
```

This path requires JDK {minimum_runtime}+ and Maven. The source build and the minimal example
below were verified together at revision `{source_revision}`.
