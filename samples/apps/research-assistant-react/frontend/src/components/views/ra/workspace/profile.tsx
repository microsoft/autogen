import {
  ChevronLeftIcon,
  ChevronRightIcon,
  PencilIcon,
  UserCircleIcon,
} from "@heroicons/react/24/outline";
import * as React from "react";
import ClearDBView from "./cleardb";
import { IStatus } from "../../../types";
import { appContext } from "../../../../hooks/provider";
import { Button, Modal, Switch, message } from "antd";
import { fetchJSON, truncateText } from "../../../utils";
import { LoadBox } from "../../../atoms";
import { set, update } from "lodash";
import TextArea from "antd/es/input/TextArea";

const ProfileView = ({ config }: any) => {
  // console.log("config", config);
  const [profileLoading, setProfileLoading] = React.useState(false);
  const [isOpen, setIsOpen] = React.useState(false);

  const serverUrl = process.env.GATSBY_API_URL;

  const { user } = React.useContext(appContext);
  const fetchProfileUrl = `${serverUrl}/profile?user_id=${user?.email}`;
  const updateProfileUrl = `${serverUrl}/profile`;
  const refreshProfileUrl = `${serverUrl}/profile/refresh?user_id=${user?.email}`;
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const [personalization, setPersonalization] = React.useState(false);

  const [profile, setProfile] = React.useState<any>("");
  const [textChanged, setTextChanged] = React.useState(false);

  const profileDivRef = React.useRef<HTMLDivElement>(null);

  const togglePersonalization = (checked: boolean) => {
    console.log(`switch to ${checked}`);
    setPersonalization(checked);
  };
  const fetchProfile = () => {
    setError(null);
    setProfileLoading(true);
    // const fetch;
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      console.log(data);
      if (data && data.status) {
        message.success(data.message);
        setProfile(data.data.profile);
      } else {
        message.error(data.message);
      }
      setProfileLoading(false);
    };
    const onError = (err: any) => {
      setError(err);

      message.error(err.message);
      setProfileLoading(false);
    };
    fetchJSON(fetchProfileUrl, payLoad, onSuccess, onError);
  };

  const updateProfile = (profile: string) => {
    setError(null);
    setProfileLoading(true);
    // const fetch;
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ userId: user?.email, profile: profile }),
    };

    const onSuccess = (data: any) => {
      console.log(data);
      if (data && data.status) {
        message.success(data.message);
        setProfile(data.data.profile);
        console.log("updated profile", data);
      } else {
        message.error(data.message);
      }
      setProfileLoading(false);
    };

    const onError = (err: any) => {
      setError(err);

      message.error(err.message);
      setProfileLoading(false);
    };
    fetchJSON(updateProfileUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (profileLoading === false) {
      setTextChanged(false);
    }
  }, [profileLoading]);

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchProfile();
    }
  }, []);

  const refreshProfile = () => {
    setError(null);
    setProfileLoading(true);
    // const fetch;
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      console.log(data);
      if (data && data.status) {
        message.success(data.message);
        setProfile(data.data.profile);
      } else {
        message.error(data.message);
      }
      setProfileLoading(false);
    };

    const onError = (err: any) => {
      setError(err);

      message.error(err.message);
      setProfileLoading(false);
    };
    fetchJSON(refreshProfileUrl, payLoad, onSuccess, onError);
  };

  // const minWidth = isOpen ? "200px" : "50px";
  return (
    <div className="">
      <div className="mt-">
        <Modal
          title="Profile"
          width={800}
          open={isOpen}
          onOk={() => {
            setIsOpen(!isOpen);
            updateProfile(profile);
          }}
          onCancel={() => setIsOpen(!isOpen)}
        >
          <>
            <div className="text-xs mb-2 break-words">
              Your personalization profile is shown below
              <div
                role="button"
                onClick={() => {
                  refreshProfile();
                }}
                className="text-xs text-accent inline-block mx-2"
              >
                refresh
              </div>{" "}
            </div>
            {profileLoading && <LoadBox subtitle={"refreshing profile .."} />}

            <TextArea
              autoSize={{ minRows: 6, maxRows: 10 }}
              ref={profileDivRef}
              defaultValue={profile}
              value={profile}
              className="pt-3 break-words"
              onChange={(e) => {
                setProfile(e.target.value);
              }}
              disabled={profileLoading}
              onPressEnter={(e) => {
                e.preventDefault();
                console.log("enter pressed", e.target?.value);
                const innerText = e.target?.value;
                updateProfile(innerText);
                // updateProfile(profileDivRef.current?.innerText || "");
              }}
            />

            <div className="mt-2">
              <div className="text-xs my-2 ">
                {" "}
                Turn {`${personalization ? "OFF" : "ON"}`} personalization .
              </div>
              <Switch
                defaultChecked={config.get.personalize}
                onChange={(checked) => {
                  config.set({ ...config.get, personalize: checked });
                  togglePersonalization(checked);
                }}
              />
            </div>
          </>
        </Modal>
        <hr className="mb-2" />

        <Button
          className="block w-full "
          loading={profileLoading}
          type="default"
          onClick={() => {
            setIsOpen(true);
          }}
        >
          {!profileLoading && (
            <>
              <UserCircleIcon className="w-5, h-5 inline-block mr-1" />
              View Profile
            </>
          )}
          {profileLoading && <LoadBox subtitle={"fetching profile .."} />}
        </Button>

        {/* <div
          role="button"
          className="inline-block text-xs hover:text-accent"
          onClick={() => {
            setIsOpen(true);
          }}
        >
          {!profileLoading && (
            <>
              <UserCircleIcon className="w-5, h-5 inline-block mr-1" />
              View Profile
            </>
          )}
          {profileLoading && <LoadBox subtitle={"fetching profile .."} />}
        </div> */}
      </div>
    </div>
  );
};

export default ProfileView;
