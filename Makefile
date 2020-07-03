PY2 = python
PY3 = python3
TWINE = twine


clean:
	grep '/$$' .gitignore \
		| xargs -I{} echo "\\! -path '*/{}*'" \
		| tr $$'\n' ' ' | xargs find . -name '*.pyc' \
		| xargs -n1 rm

