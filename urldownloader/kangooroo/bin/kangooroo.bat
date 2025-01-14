@rem
@rem Copyright 2015 the original author or authors.
@rem
@rem Licensed under the Apache License, Version 2.0 (the "License");
@rem you may not use this file except in compliance with the License.
@rem You may obtain a copy of the License at
@rem
@rem      https://www.apache.org/licenses/LICENSE-2.0
@rem
@rem Unless required by applicable law or agreed to in writing, software
@rem distributed under the License is distributed on an "AS IS" BASIS,
@rem WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
@rem See the License for the specific language governing permissions and
@rem limitations under the License.
@rem

@if "%DEBUG%" == "" @echo off
@rem ##########################################################################
@rem
@rem  kangooroo startup script for Windows
@rem
@rem ##########################################################################

@rem Set local scope for the variables with windows NT shell
if "%OS%"=="Windows_NT" setlocal

set DIRNAME=%~dp0
if "%DIRNAME%" == "" set DIRNAME=.
set APP_BASE_NAME=%~n0
set APP_HOME=%DIRNAME%..

@rem Resolve any "." and ".." in APP_HOME to make it shorter.
for %%i in ("%APP_HOME%") do set APP_HOME=%%~fi

@rem Add default JVM options here. You can also use JAVA_OPTS and KANGOOROO_OPTS to pass JVM options to this script.
set DEFAULT_JVM_OPTS=

@rem Find java.exe
if defined JAVA_HOME goto findJavaFromJavaHome

set JAVA_EXE=java.exe
%JAVA_EXE% -version >NUL 2>&1
if "%ERRORLEVEL%" == "0" goto execute

echo.
echo ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH.
echo.
echo Please set the JAVA_HOME variable in your environment to match the
echo location of your Java installation.

goto fail

:findJavaFromJavaHome
set JAVA_HOME=%JAVA_HOME:"=%
set JAVA_EXE=%JAVA_HOME%/bin/java.exe

if exist "%JAVA_EXE%" goto execute

echo.
echo ERROR: JAVA_HOME is set to an invalid directory: %JAVA_HOME%
echo.
echo Please set the JAVA_HOME variable in your environment to match the
echo location of your Java installation.

goto fail

:execute
@rem Setup the command line

set CLASSPATH=%APP_HOME%\lib\kangooroo-v2.0.1.dev0.jar;%APP_HOME%\lib\browserup-proxy-2.1.2.zip;%APP_HOME%\lib\browserup-proxy-rest-2.1.2.jar;%APP_HOME%\lib\browserup-proxy-core-2.1.2.jar;%APP_HOME%\lib\sitebricks-0.8.11.jar;%APP_HOME%\lib\jersey-media-json-jackson-2.31.jar;%APP_HOME%\lib\swagger-jaxrs2-2.1.2.jar;%APP_HOME%\lib\swagger-integration-2.1.2.jar;%APP_HOME%\lib\swagger-core-2.1.2.jar;%APP_HOME%\lib\sitebricks-client-0.8.11.jar;%APP_HOME%\lib\sitebricks-converter-0.8.11.jar;%APP_HOME%\lib\jackson-jaxrs-json-provider-2.12.1.jar;%APP_HOME%\lib\jackson-module-jaxb-annotations-2.12.1.jar;%APP_HOME%\lib\jackson-datatype-jsr310-2.12.1.jar;%APP_HOME%\lib\jackson-jaxrs-base-2.12.1.jar;%APP_HOME%\lib\jackson-databind-2.12.1.jar;%APP_HOME%\lib\swagger-models-2.1.2.jar;%APP_HOME%\lib\jackson-annotations-2.12.1.jar;%APP_HOME%\lib\jackson-core-2.12.1.jar;%APP_HOME%\lib\jackson-dataformat-yaml-2.12.1.jar;%APP_HOME%\lib\snakeyaml-1.28.jar;%APP_HOME%\lib\selenium-java-3.141.59.jar;%APP_HOME%\lib\selenium-chrome-driver-3.141.59.jar;%APP_HOME%\lib\selenium-support-3.141.59.jar;%APP_HOME%\lib\selenium-edge-driver-3.141.59.jar;%APP_HOME%\lib\selenium-firefox-driver-3.141.59.jar;%APP_HOME%\lib\selenium-ie-driver-3.141.59.jar;%APP_HOME%\lib\selenium-opera-driver-3.141.59.jar;%APP_HOME%\lib\selenium-safari-driver-3.141.59.jar;%APP_HOME%\lib\selenium-remote-driver-3.141.59.jar;%APP_HOME%\lib\selenium-api-3.141.59.jar;%APP_HOME%\lib\fluent-hc-4.5.13.jar;%APP_HOME%\lib\log4j-slf4j2-impl-2.22.0.jar;%APP_HOME%\lib\log4j-core-2.22.0.jar;%APP_HOME%\lib\log4j-api-2.22.0.jar;%APP_HOME%\lib\browserup-proxy-mitm-2.1.2.jar;%APP_HOME%\lib\littleproxy-2.0.0-beta-5.jar;%APP_HOME%\lib\dnsjava-3.1.0.jar;%APP_HOME%\lib\jcl-over-slf4j-1.7.30.jar;%APP_HOME%\lib\async-http-client-1.6.3.jar;%APP_HOME%\lib\slf4j-api-2.0.9.jar;%APP_HOME%\lib\commons-cli-1.4.jar;%APP_HOME%\lib\commons-io-2.5.jar;%APP_HOME%\lib\commons-net-3.7.2.jar;%APP_HOME%\lib\commons-text-1.9.jar;%APP_HOME%\lib\commons-lang3-3.11.jar;%APP_HOME%\lib\lombok-1.18.12.jar;%APP_HOME%\lib\netty-all-4.1.50.Final.jar;%APP_HOME%\lib\gson-2.8.6.jar;%APP_HOME%\lib\netty-codec-4.1.50.Final.jar;%APP_HOME%\lib\jaxb-api-2.3.1.jar;%APP_HOME%\lib\guice-servlet-4.2.3.jar;%APP_HOME%\lib\guice-multibindings-4.2.3.jar;%APP_HOME%\lib\guice-4.2.3.jar;%APP_HOME%\lib\guava-28.2-jre.jar;%APP_HOME%\lib\jzlib-1.1.3.jar;%APP_HOME%\lib\bcpkix-jdk15on-1.64.jar;%APP_HOME%\lib\bcprov-jdk15on-1.64.jar;%APP_HOME%\lib\dec-0.1.2.jar;%APP_HOME%\lib\jersey-hk2-2.31.jar;%APP_HOME%\lib\javassist-3.27.0-GA.jar;%APP_HOME%\lib\jetty-servlet-9.4.29.v20200521.jar;%APP_HOME%\lib\jetty-security-9.4.29.v20200521.jar;%APP_HOME%\lib\jetty-server-9.4.29.v20200521.jar;%APP_HOME%\lib\byte-buddy-1.8.15.jar;%APP_HOME%\lib\commons-exec-1.3.jar;%APP_HOME%\lib\okhttp-3.11.0.jar;%APP_HOME%\lib\okio-1.14.0.jar;%APP_HOME%\lib\httpclient-4.5.13.jar;%APP_HOME%\lib\commons-logging-1.2.jar;%APP_HOME%\lib\netty-transport-4.1.50.Final.jar;%APP_HOME%\lib\netty-buffer-4.1.50.Final.jar;%APP_HOME%\lib\netty-resolver-4.1.50.Final.jar;%APP_HOME%\lib\netty-common-4.1.50.Final.jar;%APP_HOME%\lib\barchart-udt-bundle-2.3.0.jar;%APP_HOME%\lib\javax.activation-api-1.2.0.jar;%APP_HOME%\lib\failureaccess-1.0.1.jar;%APP_HOME%\lib\listenablefuture-9999.0-empty-to-avoid-conflict-with-guava.jar;%APP_HOME%\lib\jsr305-3.0.2.jar;%APP_HOME%\lib\checker-qual-2.10.0.jar;%APP_HOME%\lib\error_prone_annotations-2.3.4.jar;%APP_HOME%\lib\j2objc-annotations-1.3.jar;%APP_HOME%\lib\jopt-simple-5.0.4.jar;%APP_HOME%\lib\jersey-container-servlet-core-2.31.jar;%APP_HOME%\lib\jersey-bean-validation-2.31.jar;%APP_HOME%\lib\swagger-jaxrs2-servlet-initializer-2.1.2.jar;%APP_HOME%\lib\javax.inject-1.jar;%APP_HOME%\lib\aopalliance-1.0.jar;%APP_HOME%\lib\sitebricks-annotations-0.8.11.jar;%APP_HOME%\lib\mvel2-2.1.3.Final.jar;%APP_HOME%\lib\jcip-annotations-1.0.jar;%APP_HOME%\lib\annotations-7.0.3.jar;%APP_HOME%\lib\jsoup-1.8.1.jar;%APP_HOME%\lib\javax.servlet-api-3.1.0.jar;%APP_HOME%\lib\jetty-http-9.4.29.v20200521.jar;%APP_HOME%\lib\jetty-io-9.4.29.v20200521.jar;%APP_HOME%\lib\httpcore-4.4.13.jar;%APP_HOME%\lib\commons-codec-1.11.jar;%APP_HOME%\lib\jersey-server-2.31.jar;%APP_HOME%\lib\jersey-client-2.31.jar;%APP_HOME%\lib\jersey-media-jaxb-2.31.jar;%APP_HOME%\lib\jersey-common-2.31.jar;%APP_HOME%\lib\hk2-locator-2.6.1.jar;%APP_HOME%\lib\hk2-api-2.6.1.jar;%APP_HOME%\lib\hk2-utils-2.6.1.jar;%APP_HOME%\lib\jakarta.inject-2.6.1.jar;%APP_HOME%\lib\jersey-entity-filtering-2.31.jar;%APP_HOME%\lib\jakarta.ws.rs-api-2.1.6.jar;%APP_HOME%\lib\hibernate-validator-6.1.2.Final.jar;%APP_HOME%\lib\jakarta.validation-api-2.0.2.jar;%APP_HOME%\lib\jakarta.el-api-3.0.3.jar;%APP_HOME%\lib\jakarta.el-3.0.3.jar;%APP_HOME%\lib\classgraph-4.8.65.jar;%APP_HOME%\lib\swagger-annotations-2.1.2.jar;%APP_HOME%\lib\jakarta.xml.bind-api-2.3.2.jar;%APP_HOME%\lib\xstream-1.3.1.jar;%APP_HOME%\lib\jetty-util-9.4.29.v20200521.jar;%APP_HOME%\lib\jakarta.annotation-api-1.3.5.jar;%APP_HOME%\lib\osgi-resource-locator-1.0.3.jar;%APP_HOME%\lib\aopalliance-repackaged-2.6.1.jar;%APP_HOME%\lib\jboss-logging-3.3.2.Final.jar;%APP_HOME%\lib\classmate-1.3.4.jar;%APP_HOME%\lib\jakarta.activation-api-1.2.1.jar;%APP_HOME%\lib\xpp3_min-1.1.4c.jar


@rem Execute kangooroo
"%JAVA_EXE%" %DEFAULT_JVM_OPTS% %JAVA_OPTS% %KANGOOROO_OPTS%  -classpath "%CLASSPATH%" ca.gc.cyber.kangooroo.KangoorooStandaloneRunner %*

:end
@rem End local scope for the variables with windows NT shell
if "%ERRORLEVEL%"=="0" goto mainEnd

:fail
rem Set variable KANGOOROO_EXIT_CONSOLE if you need the _script_ return code instead of
rem the _cmd.exe /c_ return code!
if  not "" == "%KANGOOROO_EXIT_CONSOLE%" exit 1
exit /b 1

:mainEnd
if "%OS%"=="Windows_NT" endlocal

:omega
