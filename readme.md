Maybe I'll add docs, Maybe I won't!


# How to use

1. Read through the code (Because I'm a random stranger on the internet)

2. Enter `pip install pygamenu`

3. Put `Import pymenu as pm` in your code

4. Code some stuff in a `.pym` file according to the docs (If those don't exist just look at the example really hard)

5. Create a view using this syntax`View = pm.initialize('path_from_working_dir/abcd.pym', size:Point)`

6. In your main loop add 
```python
for event in pg.event.get():

    View.passEvent(event, globals())
``` 

7. Read the docs for more info (Or do trial and error and try to figure out what my custom error messages mean)


Github:
https://github.com/Camleaf/Pymenu
Pypi:
https://pypi.org/project/pygamenu/
