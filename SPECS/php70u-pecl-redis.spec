# IUS spec file for php70u-pecl-redis, forked from:
#
# Fedora spec file for php-pecl-redis
#
# Copyright (c) 2012-2016 Remi Collet
# License: CC-BY-SA
# http://creativecommons.org/licenses/by-sa/4.0/
#
# Please, preserve the changelog entries
#
%global pecl_name redis
%global ini_name  50-%{pecl_name}.ini
%global php       php70u

%bcond_without zts
%bcond_without tests
%bcond_without igbinary

Summary:        Extension for communicating with the Redis key-value store
Name:           %{php}-pecl-%{pecl_name}
Version:        3.1.6
Release:        1.ius%{?dist}
License:        PHP
URL:            http://pecl.php.net/package/%{pecl_name}
Source0:        http://pecl.php.net/get/%{pecl_name}-%{version}.tgz

BuildRequires:  %{php}-devel
BuildRequires:  %{php}-pear
%{?with_igbinary:BuildRequires: %{php}-pecl-igbinary-devel}
%{?with_tests:BuildRequires: redis >= 2.6}

Requires:       php(zend-abi) = %{php_zend_api}
Requires:       php(api) = %{php_core_api}
%{?with_igbinary:Requires: %{php}-pecl-igbinary%{?_isa}}

Requires(post): %{php}-pear
Requires(postun): %{php}-pear

# provide the stock name
Provides:       php-pecl-%{pecl_name} = %{version}
Provides:       php-pecl-%{pecl_name}%{?_isa} = %{version}

# provide the stock and IUS names without pecl
Provides:       php-%{pecl_name} = %{version}
Provides:       php-%{pecl_name}%{?_isa} = %{version}
Provides:       %{php}-%{pecl_name} = %{version}
Provides:       %{php}-%{pecl_name}%{?_isa} = %{version}

# provide the stock and IUS names in pecl() format
Provides:       php-pecl(%{pecl_name}) = %{version}
Provides:       php-pecl(%{pecl_name})%{?_isa} = %{version}
Provides:       %{php}-pecl(%{pecl_name}) = %{version}
Provides:       %{php}-pecl(%{pecl_name})%{?_isa} = %{version}

# conflict with the stock name
Conflicts:      php-pecl-%{pecl_name} < %{version}

%{?filter_provides_in: %filter_provides_in %{php_extdir}/.*\.so$}
%{?filter_provides_in: %filter_provides_in %{php_ztsextdir}/.*\.so$}
%{?filter_setup}


%description
The phpredis extension provides an API for communicating
with the Redis key-value store.

This Redis client implements most of the latest Redis API.
As method only only works when also implemented on the server side,
some doesn't work with an old redis server version.


%prep
%setup -q -c

# Don't install/register tests
sed -e 's/role="test"/role="src"/' \
    -e '/COPYING/s/role="doc"/role="src"/' \
    -i package.xml

# rename source folder
mv %{pecl_name}-%{version} NTS

# Sanity check, really often broken
extver=$(sed -n '/#define PHP_REDIS_VERSION/{s/.* "//;s/".*$//;p}' NTS/php_redis.h)
if test "x${extver}" != "x%{version}"; then
   : Error: Upstream extension version is ${extver}, expecting %{version}.
   exit 1
fi

%{?with_zts:cp -pr NTS ZTS}

cat > %{ini_name} << EOF
; Enable %{pecl_name} extension module
extension = %{pecl_name}.so

; phpredis can be used to store PHP sessions.
; To do this, uncomment and configure below

; RPM note : save_handler and save_path are defined
; for mod_php, in /etc/httpd/conf.d/php.conf
; for php-fpm, in %{_sysconfdir}/php-fpm.d/*conf

;session.save_handler = %{pecl_name}
;session.save_path = "tcp://host1:6379?weight=1, tcp://host2:6379?weight=2&timeout=2.5, tcp://host3:6379?weight=2"

; Configuration
;redis.arrays.names = ''
;redis.arrays.hosts = ''
;redis.arrays.previous = ''
;redis.arrays.functions = ''
;redis.arrays.index = ''
;redis.arrays.autorehash = ''
;redis.clusters.seeds = ''
;redis.clusters.timeout = ''
;redis.clusters.read_timeout = ''
EOF


%build
pushd NTS
%{_bindir}/phpize
%configure \
    --enable-redis \
    --enable-redis-session \
%{?with_igbinary: --enable-redis-igbinary} \
    --with-php-config=%{_bindir}/php-config
make %{?_smp_mflags}
popd

%if %{with zts}
pushd ZTS
%{_bindir}/zts-phpize
%configure \
    --enable-redis \
    --enable-redis-session \
%{?with_igbinary: --enable-redis-igbinary} \
    --with-php-config=%{_bindir}/zts-php-config
make %{?_smp_mflags}
popd
%endif


%install
make -C NTS install INSTALL_ROOT=%{buildroot}
install -D -p -m 644 %{ini_name} %{buildroot}%{php_inidir}/%{ini_name}

%if %{with zts}
make -C ZTS install INSTALL_ROOT=%{buildroot}
install -D -p -m 644 %{ini_name} %{buildroot}%{php_ztsinidir}/%{ini_name}
%endif

install -D -p -m 644 package.xml %{buildroot}%{pecl_xmldir}/%{pecl_name}.xml

pushd NTS
for i in $(grep 'role="doc"' ../package.xml | sed -e 's/^.*name="//;s/".*$//')
do install -D -p -m 644 $i %{buildroot}%{pecl_docdir}/%{pecl_name}/$i
done
popd


%check
%{__php} --no-php-ini \
%{?with_igbinary: --define extension=igbinary.so} \
    --define extension=%{buildroot}%{php_extdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}

%if %{with zts}
%{__ztsphp} --no-php-ini \
%{?with_igbinary: --define extension=igbinary.so} \
    --define extension=%{buildroot}%{php_ztsextdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}
%endif

%if %{with tests}
pushd NTS/tests

# Launch redis server
mkdir -p data
pidfile=$PWD/redis.pid
# use a random port to avoid conflicts
port=%(shuf -i 6000-6999 -n 1)
%{_bindir}/redis-server   \
    --bind      127.0.0.1      \
    --port      $port          \
    --daemonize yes            \
    --logfile   $PWD/redis.log \
    --dir       $PWD/data      \
    --pidfile   $pidfile

sed -e "s/6379/$port/" -i RedisTest.php

# Run the test Suite
ret=0
%{__php} --no-php-ini \
%{?with_igbinary: --define extension=igbinary.so} \
    --define extension=%{buildroot}%{php_extdir}/%{pecl_name}.so \
    TestRedis.php || ret=1

# Cleanup
if [ -f $pidfile ]; then
   %{_bindir}/redis-cli -p $port shutdown
fi

popd
exit $ret

%else
: Upstream test suite disabled
%endif


%post
%{pecl_install} %{pecl_xmldir}/%{pecl_name}.xml >/dev/null || :


%postun
if [ $1 -eq 0 ]; then
    %{pecl_uninstall} %{pecl_name} >/dev/null || :
fi


%files
%license NTS/COPYING
%doc %{pecl_docdir}/%{pecl_name}
%{pecl_xmldir}/%{pecl_name}.xml

%{php_extdir}/%{pecl_name}.so
%config(noreplace) %{php_inidir}/%{ini_name}

%if %{with zts}
%{php_ztsextdir}/%{pecl_name}.so
%config(noreplace) %{php_ztsinidir}/%{ini_name}
%endif


%changelog
* Wed Jan 03 2018 Ben Harper <ben.harper@rackspace.com> - 3.1.6-1.ius
- Latest upstream

* Tue Jan 02 2018 Ben Harper <ben.harper@rackspace.com> - 3.1.5-1.ius
- Latest upstream
- Remove Patch0, fixed upstream

* Wed Nov 08 2017 Carl George <carl@george.computer> - 3.1.4-2.ius
- Backport upstream fix for https://github.com/phpredis/phpredis/issues/1210

* Wed Sep 27 2017 Ben Harper <ben.harper@rackspace.com> - 3.1.4-1.ius
- Latest upstream

* Thu Jul 27 2017 Carl George <carl@george.computer> - 3.1.3-2.ius
- Enable igbinary

* Mon Jul 17 2017 Ben Harper <ben.harper@rackspace.com> - 3.1.3-1.ius
- Latest upstream

* Mon Mar 27 2017 Ben Harper <ben.harper@rackspace.com> - 3.1.2-1.ius
- Latest upstream

* Wed Feb 01 2017 Ben Harper <ben.harper@rackspace.com> - 3.1.1-1.ius
- Latest upstream
- remove Patch1, fixed upstream
- changes to Launch redis server and Cleanup from Fedora:
  http://pkgs.fedoraproject.org/cgit/rpms/php-pecl-redis.git/commit/?id=676cb4cd0326b8e5e9cf49ed3c7cfef31d804543

* Thu Jun 16 2016 Carl George <carl.george@rackspace.com> - 3.0.0-2.ius
- Clean up auto-provides filters

* Mon Jun 13 2016 Carl George <carl.george@rackspace.com> - 3.0.0-1.ius
- Port from Fedora to IUS
- Latest upstream
- Re-add scriptlets (file triggers not yet available in EL)
- Filter auto-provides
- Add %%license compatibility trick
- Preserve timestamps when installing files
- Disable igbinary support
- Add Patch1 to skip testExpireAtWithLong on 32bit build (gh#838)
- Use a random port in %%check to avoid conflicts

* Thu Jun  9 2016 Remi Collet <remi@fedoraproject.org> - 2.2.8-1
- Update to 2.2.8 (stable)
- don't install/register tests

* Sat Feb 13 2016 Remi Collet <remi@fedoraproject.org> - 2.2.7-4
- drop scriptlets (replaced by file triggers in php-pear)
- cleanup

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 2.2.7-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.7-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Tue Mar 03 2015 Remi Collet <remi@fedoraproject.org> - 2.2.7-1
- Update to 2.2.7 (stable)

* Sun Aug 17 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.5-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Thu Jun 19 2014 Remi Collet <rcollet@redhat.com> - 2.2.5-4
- rebuild for https://fedoraproject.org/wiki/Changes/Php56

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.5-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Thu Apr 24 2014 Remi Collet <rcollet@redhat.com> - 2.2.5-2
- add numerical prefix to extension configuration file
- add comment about session configuration
- fix memory corruption with PHP 5.6
  https://github.com/nicolasff/phpredis/pull/447

* Wed Mar 19 2014 Remi Collet <remi@fedoraproject.org> - 2.2.5-1
- Update to 2.2.5

* Thu Mar 13 2014 Remi Collet <remi@fedoraproject.org> - 2.2.4-2
- cleanups
- move doc in pecl_docdir
- run upstream tests only with --with tests option

* Mon Sep 09 2013 Remi Collet <remi@fedoraproject.org> - 2.2.4-1
- Update to 2.2.4

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.3-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Apr 30 2013 Remi Collet <remi@fedoraproject.org> - 2.2.3-1
- update to 2.2.3
- upstream moved to pecl, rename from php-redis to php-pecl-redis

* Tue Sep 11 2012 Remi Collet <remi@fedoraproject.org> - 2.2.2-5.git6f7087f
- more docs and improved description

* Sun Sep  2 2012 Remi Collet <remi@fedoraproject.org> - 2.2.2-4.git6f7087f
- latest snahot (without bundled igbinary)
- remove chmod (done upstream)

* Sat Sep  1 2012 Remi Collet <remi@fedoraproject.org> - 2.2.2-3.git5df5153
- run only test suite with redis > 2.4

* Fri Aug 31 2012 Remi Collet <remi@fedoraproject.org> - 2.2.2-2.git5df5153
- latest master
- run test suite

* Wed Aug 29 2012 Remi Collet <remi@fedoraproject.org> - 2.2.2-1
- update to 2.2.2
- enable ZTS build

* Tue Aug 28 2012 Remi Collet <remi@fedoraproject.org> - 2.2.1-1
- initial package

