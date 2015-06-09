#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Copyright (c) 2013 by Lukasz Janyst <ljanyst@buggybrain.net>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED 'AS IS' AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#-------------------------------------------------------------------------------

import sys
import uuid
import getopt
import getpass
import carddav
import vobject

#-------------------------------------------------------------------------------
# Fix FN
#-------------------------------------------------------------------------------
def fixFN( url, filename, user, passwd, auth, verify ):
    print '[i] Editing at', url, '...'
    print '[i] Listing the addressbook...'
    dav    = carddav.PyCardDAV( url, user=user, passwd=passwd, auth=auth,
                                write_support=True, verify=verify )
    abook  = dav.get_abook()
    nCards = len( abook.keys() )
    print '[i] Found', nCards, 'cards.'

    curr = 1
    for href, etag in abook.items():
        print "\r[i] Processing", curr, "of", nCards,
        sys.stdout.flush()
        curr += 1
        card = dav.get_vcard( href )
        card = card.split( '\r\n' )

        cardFixed = []
        for l in card:
            if not l.startswith( 'FN:' ):
                cardFixed.append( l )
        cardFixed = '\r\n'.join( cardFixed )

        c = vobject.readOne( cardFixed )

        n = [c.n.value.prefix, c.n.value.given, c.n.value.additional,
             c.n.value.family, c.n.value.suffix]
        name = ''
        for part in n:
            if part:
                name += part + ' '
        name = name.strip()
 
        if not hasattr( c, 'fn' ):
            c.add('fn')
        c.fn.value = name

        try:
            dav.update_vcard( c.serialize().decode( 'utf-8' ), href, etag )
        except Exception, e:
            print ''
            raise
    print ''
    print '[i] All updated'

#-------------------------------------------------------------------------------
# Download
#-------------------------------------------------------------------------------
def download( url, filename, user, passwd, auth, verify ):
    print '[i] Downloading from', url, 'to', filename, '...'
    print '[i] Downloading the addressbook...'
    dav    = carddav.PyCardDAV( url, user=user, passwd=passwd, auth=auth,
                                verify=verify )
    abook  = dav.get_abook()
    nCards = len( abook.keys() )
    print '[i] Found', nCards, 'cards.'

    f = open( filename, 'w' )

    curr = 1
    for href, etag in abook.items():
        print "\r[i] Fetching", curr, "of", nCards,
        sys.stdout.flush()
        curr += 1
        card = dav.get_vcard( href )
        f.write( card + '\n' )
    print ''
    f.close()
    print '[i] All saved to:', filename

#-------------------------------------------------------------------------------
# Upload
#-------------------------------------------------------------------------------
def upload( url, filename, user, passwd, auth, verify ):
    if not url.endswith( '/' ):
        url += '/'

    print '[i] Uploading from', filename, 'to', url, '...'

    print '[i] Processing cards in', filename, '...'
    f = open( filename, 'r' )
    cards = []
    for card in vobject.readComponents( f, validate=True ):
        cards.append( card )
    nCards = len(cards)
    print '[i] Successfuly read and validated', nCards, 'entries'

    print '[i] Connecting to', url, '...'
    dav = carddav.PyCardDAV( url, user=user, passwd=passwd, auth=auth,
                             write_support=True, verify=verify )

    curr = 1
    for card in cards:
        print "\r[i] Uploading", curr, "of", nCards,
        sys.stdout.flush()
        curr += 1

        if hasattr(card, 'prodid' ):
            del card.prodid

        if not hasattr( card, 'uid' ):
            card.add('uid')
        card.uid.value = str( uuid.uuid4() )
        try:
            dav.upload_new_card( card.serialize().decode('utf-8') )
        except Exception, e:
            print ''
            raise
    print ''
    f.close()
    print '[i] All done'

#-------------------------------------------------------------------------------
# Print help
#-------------------------------------------------------------------------------
def printHelp():
    print( 'carddav-util.py [options]' )
    print( ' --url=http://your.addressbook.com CardDAV addressbook           ' )
    print( ' --file=local.vcf                  local vCard file              ' )
    print( ' --user=username                   username                      ' )
    print( ' --passwd=password                 password, if absent will      ' )
    print( '                                   prompt for it in the console  ' )
    print( ' --download                        copy server -> file           ' )
    print( ' --upload                          copy file -> server           ' )
    print( ' --fixfn                           regenerate the FN tag         ' )
    print( ' --digest                          use digest authentication     ' )
    print( ' --no-cert-verify                  skip certificate verification ' )
    print( ' --help                            this help message             ' )

#-------------------------------------------------------------------------------
# Run the show
#-------------------------------------------------------------------------------
def main():
    try:
        params = ['url=', 'file=', 'download', 'upload', 'help',
                  'user=', 'passwd=', 'digest', 'no-cert-verify', 'fixfn']
        optlist, args = getopt.getopt( sys.argv[1:], '', params )
    except getopt.GetoptError, e:
        print '[!]', e
        return 1

    opts = dict(optlist)
    if '--help' in opts or not opts:
        printHelp()
        return 0

    if '--upload' in opts and '--download' in opts and '--fixfn' in opts:
        print '[!] You can only choose one action at a time'
        return 2

    if '--url' not in opts or '--file' not in opts:
        print '[!] You must specify both the filename and the url'
        return 3

    url      = opts['--url']
    filename = opts['--file']

    user   = None
    passwd = None
    auth   = 'basic'
    verify = True

    if '--digest' in opts:
        auth = 'digest'

    if '--no-cert-verify' in opts:
        verify = False

    if '--user' in opts:
        user = opts['--user']
        if '--passwd' in opts:
            passwd = opts['--passwd']
        else:
            passwd = getpass.getpass( user+'\'s password (won\'t be echoed): ')

    commandMap = {'--upload': upload, '--download': download, '--fixfn': fixFN}
    for command in commandMap:
        if command in opts:
            i = 0
            try:
                i = commandMap[command]( url, filename, user, passwd, auth, verify )
            except Exception, e:
                print '[!]', e

if __name__ == '__main__':
    sys.exit(main())
