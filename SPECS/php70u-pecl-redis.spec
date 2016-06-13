# Fedora spec file for php-pecl-redis
#
# Copyright (c) 2012-2016 Remi Collet
# License: CC-BY-SA
# http://creativecommons.org/licenses/by-sa/4.0/
#
# Please, preserve the changelog entries
#
%global pecl_name   redis
%global with_zts    0%{?__ztsphp:1}
%global with_tests  0%{?_with_tests:1}
%global ini_name    50-%{pecl_name}.ini

Summary:       Extension for communicating with the Redis key-value store
Name:          php-pecl-redis
Version:       2.2.8
Release:       1%{?dist}
License:       PHP
Group:         Development/Languages
URL:           http://pecl.php.net/package/redis
Source0:       http://pecl.php.net/get/%{pecl_name}-%{version}.tgz

BuildRequires: php-devel
BuildRequires: php-pear
BuildRequires: php-pecl-igbinary-devel
# to run Test suite
%if %{with_tests}
BuildRequires: redis >= 2.6
%endif

Requires:      php(zend-abi) = %{php_zend_api}
Requires:      php(api) = %{php_core_api}
# php-pecl-igbinary missing php-pecl(igbinary)%{?_isa}
Requires:      php-pecl-igbinary%{?_isa}

Obsoletes:     php-redis < %{version}
Provides:      php-redis = %{version}-%{release}
Provides:      php-redis%{?_isa} = %{version}-%{release}
Provides:      php-pecl(%{pecl_name}) = %{version}
Provides:      php-pecl(%{pecl_name})%{?_isa} = %{version}


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

cd NTS

# Sanity check, really often broken
extver=$(sed -n '/#define PHP_REDIS_VERSION/{s/.* "//;s/".*$//;p}' php_redis.h)
if test "x${extver}" != "x%{version}"; then
   : Error: Upstream extension version is ${extver}, expecting %{version}.
   exit 1
fi
cd ..

%if %{with_zts}
# duplicate for ZTS build
cp -pr NTS ZTS
%endif

# Drop in the bit of configuration
cat > %{ini_name} << 'EOF'
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
cd NTS
%{_bindir}/phpize
%configure \
    --enable-redis \
    --enable-redis-session \
    --enable-redis-igbinary \
    --with-php-config=%{_bindir}/php-config
make %{?_smp_mflags}

%if %{with_zts}
cd ../ZTS
%{_bindir}/zts-phpize
%configure \
    --enable-redis \
    --enable-redis-session \
    --enable-redis-igbinary \
    --with-php-config=%{_bindir}/zts-php-config
make %{?_smp_mflags}
%endif


%install
# Install the NTS stuff
make -C NTS install INSTALL_ROOT=%{buildroot}
install -D -m 644 %{ini_name} %{buildroot}%{php_inidir}/%{ini_name}

%if %{with_zts}
# Install the ZTS stuff
make -C ZTS install INSTALL_ROOT=%{buildroot}
install -D -m 644 %{ini_name} %{buildroot}%{php_ztsinidir}/%{ini_name}
%endif

# Install the package XML file
install -D -m 644 package.xml %{buildroot}%{pecl_xmldir}/%{name}.xml

# Documentation
cd NTS
for i in $(grep 'role="doc"' ../package.xml | sed -e 's/^.*name="//;s/".*$//')
do install -Dpm 644 $i %{buildroot}%{pecl_docdir}/%{pecl_name}/$i
done


%check
# simple module load test
%{__php} --no-php-ini \
    --define extension=igbinary.so \
    --define extension=%{buildroot}%{php_extdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}

%if %{with_zts}
%{__ztsphp} --no-php-ini \
    --define extension=igbinary.so \
    --define extension=%{buildroot}%{php_ztsextdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}
%endif

%if %{with_tests}
cd NTS/tests

# Launch redis server
mkdir -p {run,log,lib}/redis
sed -e "s:/^pidfile.*$:/pidfile $PWD/run/redis.pid:" \
    -e "s:/var:$PWD:" \
    -e "/daemonize/s/no/yes/" \
    /etc/redis.conf >redis.conf
# port number to allow 32/64 build at same time
# and avoid conflict with a possible running server
%if 0%{?__isa_bits}
port=$(expr %{__isa_bits} + 6350)
%else
%ifarch x86_64
port=6414
%else
port=6382
%endif
%endif
sed -e "s/6379/$port/" -i redis.conf
sed -e "s/6379/$port/" -i *.php
%{_bindir}/redis-server ./redis.conf

# Run the test Suite
ret=0
%{__php} --no-php-ini \
    --define extension=igbinary.so \
    --define extension=%{buildroot}%{php_extdir}/%{pecl_name}.so \
    TestRedis.php || ret=1

# Cleanup
if [ -f run/redis.pid ]; then
   kill $(cat run/redis.pid)
fi

exit $ret

%else
: Upstream test suite disabled
%endif


%files
%license NTS/COPYING
%doc %{pecl_docdir}/%{pecl_name}
%{pecl_xmldir}/%{name}.xml

%{php_extdir}/%{pecl_name}.so
%config(noreplace) %{php_inidir}/%{ini_name}

%if %{with_zts}
%{php_ztsextdir}/%{pecl_name}.so
%config(noreplace) %{php_ztsinidir}/%{ini_name}
%endif


%changelog
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

