import * as React from "react";
import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import Icon from "../components/icons";
import { appContext } from "../hooks/provider";
import { navigate } from "gatsby";
import { getCookie, setCookie } from "./utils";
import { useMsal } from "@azure/msal-react";

// markup
const LoginView = ({ meta }: any) => {
  const windowAvailable = typeof window !== "undefined";

  const clientId = process.env.GATSBY_GIT_CLIENT_ID;
  const serverUrl = process.env.GATSBY_API_URL;
  const pageUrl = windowAvailable
    ? window.location.protocol + "//" + window.location.host
    : "";
  const redirectUri = pageUrl + "/login";
  const [authStatus, setAuthStatus] = React.useState<{
    [fieldName: string]: string;
  }>({});

  const [loading, setLoading] = React.useState<boolean>(false);

  const { user, setUser, cookie_name } = React.useContext(appContext);
  const { instance, accounts, inProgress } = useMsal();

  const authError = authStatus.status === "error";
  const authColor = authError ? "orange" : "green";
  const authTextColor = "text-" + authColor + "-500";
  const authBorderColor = "border-" + authColor + "-500";

  // console.log("******* login page accounts", accounts);

  return (
    <main className=" ">
      <div className="min-h-full flex flex-col justify-center text-primary py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className=" mx-auto block   w-full  h-12  text-center text-green-600">
            <Icon icon="app" size={12} />
          </div>

          <h2 className="mt-6 text-center   text-3xl font-extrabold ">
            {meta?.title}{" "}
          </h2>
          <p className="mt-2 text-center text-sm ">{meta?.description}</p>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-6 px-4 shadow sm:rounded-lg sm:px-10">
            <div className="mt-4">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">
                    Sign in with Microsoft AD
                  </span>
                </div>
              </div>

              {!user && (
                <div>
                  <button
                    onClick={() => {
                      // login();
                      instance
                        .loginPopup()
                        .then((response) => {
                          // console.log("loginPopup", response);
                          if (response) {
                            setUser({
                              name: response.account?.name,
                              email: response.account?.username,
                              metadata: response,
                            });
                          }
                        })
                        .catch((error) => {
                          console.log("login error", error);
                          setAuthStatus({
                            status: "error",
                            statusText: error.message,
                          });
                        });
                    }}
                    type="submit"
                    className="w-full mt-4 flex justify-center py-3 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                  >
                    <Icon icon="microsoft" size={6} className="mr-2 " />
                    Sign in
                  </button>

                  {authStatus.status && (
                    <div
                      className={
                        authTextColor +
                        " " +
                        authBorderColor +
                        "  mt-3 border p-2 rounded text-sm "
                      }
                    >
                      <ExclamationTriangleIcon
                        className={
                          authTextColor + " h-5 w-5 inline-block mr-2 "
                        }
                      />
                      {authStatus.statusText}{" "}
                    </div>
                  )}

                  {loading && (
                    <div className="mt-4 p-3 text-sm border border-green-500 rounded">
                      {" "}
                      <span className="inline-block text-gray-500  mr-2">
                        <Icon icon="loading" size={4} />
                      </span>{" "}
                      Signing in ...{" "}
                    </div>
                  )}
                </div>
              )}

              {user && (
                <div className="text-gray-600 mt-4">
                  Welcome {user.name}! <br />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
};

export default LoginView;
