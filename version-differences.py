#
# Copyright (C) 2022 DANS - Data Archiving and Networked Services (info@dans.knaw.nl)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import xml.etree.ElementTree as ET
from packaging.version import parse as parse_version

PARENT_POM = 'pom.xml'
PARENT_DIR = os.path.dirname(os.getcwd())
NS = {'m': 'http://maven.apache.org/POM/4.0.0'}
third_party = set()

def extract_versions(pom_path):
    tree = ET.parse(pom_path)
    root = tree.getroot()
    props = root.find('m:properties', NS)
    dep_versions = {}
    for prop in props or []:
        if prop.tag.endswith('.version'):
            name = prop.tag.split('}', 1)[-1].replace('.version', '')
            dep_versions[name] = prop.text.strip()
    for dep_elem in root.findall('.//m:dependency', NS):
        art = dep_elem.find('m:artifactId', NS)
        ver = dep_elem.find('m:version', NS)
        grp = dep_elem.find('m:groupId', NS)
        if art is not None and ver is not None and not ver.text.startswith('${'):
            dep_versions[art.text] = ver.text
        if art is not None and grp is not None:
            if ver is not None and not ver.text.startswith('$'):
                third_party.add(f'{grp.text}:{art.text}:{ver.text}')
    return dep_versions

def check_overrides(pom_path, parent_versions):
    tree = ET.parse(pom_path)
    root = tree.getroot()
    parent_version_elem = root.find("m:parent/m:version", NS)
    parent_version_text = parent_version_elem.text.strip() if parent_version_elem is not None and parent_version_elem.text else ""
    if not parent_version_text:
        return # TODO might need to report these differently
    # align module name beyond parent version with -SNAPSHOT
    print(f'{parent_version_text:<15} {pom_path.partition("modules/")[2]}')
    module_versions = extract_versions(pom_path)
    for name, version in module_versions.items():
        parent_version = parent_versions.get(name, "N/A")
        if parent_version != "N/A" and parent_version == version:
            parent_version = 'idem'
        print(f'                          {name}: {version} parent: {parent_version}')


def find_poms(parent_dir):
    poms = []
    for root, dirs, files in os.walk(parent_dir):
        if 'target' in dirs:
            dirs.remove('target')
        if 'pom.xml' in files:
            poms.append(os.path.join(root, 'pom.xml'))
    return poms


def check_parent_versions_used(pom_path):
    tree = ET.parse(pom_path)
    root = tree.getroot()
    props = root.find('m:properties', NS)
    version_props = set()
    for prop in props or []:
        if prop.tag.endswith('.version'):
            name = prop.tag.split('}', 1)[-1].replace('.version', '')
            version_props.add(name)
    deps = set()
    for dep_elem in root.findall('.//m:dependency', NS):
        art = dep_elem.find('m:artifactId', NS)
        ver = dep_elem.find('m:version', NS)
        if art is not None and ver is not None and ver.text and ver.text.startswith('${'):
            dep_name = ver.text.strip()[2:-1].replace('.version', '')
            deps.add(dep_name)
    unused = version_props - deps
    if unused:
        print("Version properties not used in parent POM (making them mandatory in child POM's):")
        for name in sorted(unused):
            print(f"  {name}.version")
    if third_party:
        print("\nNo property for third party dependencies):")
        for dep in sorted(third_party):
            print(f'  {dep}')


def main():
    parent_versions = extract_versions(PARENT_POM)
    for pom in sorted(find_poms(PARENT_DIR)):
        if os.path.abspath(pom) != os.path.abspath(PARENT_POM):
            check_overrides(pom, parent_versions)
    check_parent_versions_used(PARENT_POM)

if __name__ == '__main__':
    main()