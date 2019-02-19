# Based on http://code.activestate.com/recipes/442299/
import glob
import os
import sys

from PIL import Image

from lxml import etree, objectify
from lxml.builder import E

class PackNode(object):
    """
    Creates an area which can recursively pack other areas of smaller sizes into itself.
    """
    def __init__(self, area):
        #if tuple contains two elements, assume they are width and height, and origin is (0,0)
        if len(area) == 2:
            area = (0,0,area[0],area[1])

        self.area = area

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, str(self.area))

    def get_width(self):
        return self.area[2] - self.area[0]
    width = property(fget=get_width)

    def get_height(self):
        return self.area[3] - self.area[1]
    height = property(fget=get_height)

    def insert(self, area):
        if hasattr(self, 'child'):
            a = self.child[0].insert(area)
            if a is None: return self.child[1].insert(area)
            return a

        area = PackNode(area)
        if area.width <= self.width and area.height <= self.height:
            self.child = [None,None]
            self.child[0] = PackNode((self.area[0]+area.width, self.area[1], self.area[2], self.area[1] + area.height))
            self.child[1] = PackNode((self.area[0], self.area[1]+area.height, self.area[2], self.area[3]))
            return PackNode((self.area[0], self.area[1], self.area[0]+area.width, self.area[1]+area.height))

def create_texturelist(input_path, images):
    size = 1024, 1024

    names = [[os.path.join(input_path, x), x] for x in list(set(images))]
    print(names)

    images = [(i.size[0] * i.size[1], name, i, basename) for name, basename, i in ((x[0], x[1], Image.open(x[0])) for x in names)]

    tree = PackNode(size)

    package_texture = []
    current_texture = []
    image_lookup = {}

    while len(images) > 0:
        images_not_used = []

        #insert each image into the PackNode area
        for area, name, img, basename in images:
            uv = tree.insert(img.size)

            if uv is None:
                images_not_used.append((area, name, img, basename))
            else:
                current_texture.append((uv, name))
                image_lookup[basename] = [uv.area, img.size]

        images = images_not_used
        tree = PackNode(size)

        package_texture.append(current_texture)
        current_texture = []

    textures = [E.texture(
        E.size(
            "{} {}".format(size[0], size[1]),
            __type="2u16",
        ),
        *[E.image(
            E.uvrect(
                "{} {} {} {}".format((texture[0].area[0] + 1) * 2, (texture[0].area[2] - 1) * 2, (texture[0].area[1] + 1) * 2, (texture[0].area[3] - 1) * 2),
                __type="4u16"
            ),
            E.imgrect(
                "{} {} {} {}".format(texture[0].area[0] * 2, texture[0].area[2] * 2, texture[0].area[1] * 2, texture[0].area[3] * 2),
                __type="4u16"
            ),
            name=os.path.splitext(os.path.basename(texture[1]))[0]
        ) for texture in package_texture[i]],
        format="argb8888rev",
        mag_filter="nearest",
        min_filter="nearest",
        name="tex{0:03d}".format(i),
        wrap_s="clamp",
        wrap_t="clamp"
    ) for i in range(0, len(package_texture))]

    texturelist = E.texturelist(
        *textures,
        compress="avslz"
    )

    return size, etree.tostring(texturelist, pretty_print=True), image_lookup
