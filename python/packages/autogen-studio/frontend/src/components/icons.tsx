import * as React from "react";

type Props = {
  icon: string;
  size: number;
  children?: React.ReactNode;
  className?: string;
};

const Icon = ({ icon = "app", size = 4, className = "" }: Props) => {
  const sizeClass = `h-${size} w-${size}  ${className}`;
  if (icon === "github") {
    return (
      <svg
        className={` ${sizeClass} inline-block  `}
        aria-hidden="true"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          fillRule="evenodd"
          d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942.359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z"
          clipRule="evenodd"
        />
      </svg>
    );
  }

  if (icon === "python") {
    return (
      <svg
        className={` ${sizeClass} inline-block  `}
        aria-hidden="true"
        fill="currentColor"
        viewBox="0 0 50 63"
      >
        <path
          d="M42.6967 62.1044H13.464C11.5281 62.1021 9.67207 61.3321 8.30315 59.9632C6.93422 58.5942 6.16417 56.7382 6.16193 54.8023V45.2659C6.16193 44.9442 6.28972 44.6357 6.5172 44.4082C6.74467 44.1807 7.0532 44.0529 7.3749 44.0529C7.6966 44.0529 8.00513 44.1807 8.2326 44.4082C8.46008 44.6357 8.58787 44.9442 8.58787 45.2659V54.8023C8.58948 56.095 9.10373 57.3344 10.0178 58.2485C10.9319 59.1626 12.1713 59.6768 13.464 59.6784H42.6967C43.9896 59.6768 45.229 59.1626 46.1433 58.2485C47.0576 57.3345 47.5721 56.0951 47.5741 54.8023V43.8746C47.5741 43.5529 47.7019 43.2444 47.9293 43.0169C48.1568 42.7894 48.4653 42.6616 48.787 42.6616C49.1087 42.6616 49.4173 42.7894 49.6447 43.0169C49.8722 43.2444 50 43.5529 50 43.8746V54.8023C49.9975 56.7383 49.2271 58.5944 47.858 59.9632C46.4889 61.3321 44.6328 62.1021 42.6967 62.1044Z"
          fill="currentColor"
        />
        <path
          d="M48.7822 41.6183C48.4605 41.6183 48.152 41.4906 47.9245 41.2631C47.697 41.0356 47.5692 40.7271 47.5692 40.4054V12.5967C47.5681 12.2529 47.4946 11.9131 47.3533 11.5995C47.212 11.286 47.0062 11.0058 46.7492 10.7773L38.0522 3.04699C37.6064 2.64832 37.0297 2.42731 36.4317 2.42595H14.677C13.0616 2.42852 11.5131 3.07163 10.3712 4.21425C9.22922 5.35686 8.58704 6.90572 8.58543 8.52114V23.3037C8.58543 23.6254 8.45764 23.9339 8.23016 24.1614C8.00268 24.3888 7.69416 24.5166 7.37246 24.5166C7.05076 24.5166 6.74223 24.3888 6.51476 24.1614C6.28728 23.9339 6.15948 23.6254 6.15948 23.3037V8.52114C6.16173 6.26251 7.05971 4.09698 8.65646 2.49955C10.2532 0.902118 12.4184 0.0032109 14.677 9.10874e-08H36.4317C37.6233 -0.000230408 38.7736 0.437008 39.6643 1.22874L48.3613 8.96024C48.8752 9.41695 49.2866 9.97738 49.5682 10.6046C49.8498 11.2318 49.9953 11.9116 49.9952 12.5992V40.4054C49.9952 40.7271 49.8674 41.0356 49.6399 41.2631C49.4124 41.4906 49.1039 41.6183 48.7822 41.6183Z"
          fill="currentColor"
        />
        <path
          d="M48.7203 13.1681H41.474C40.1838 13.1665 38.947 12.6533 38.0347 11.741C37.1224 10.8287 36.6091 9.59184 36.6075 8.30167V1.49325C36.6075 1.17155 36.7353 0.863022 36.9628 0.635545C37.1903 0.408069 37.4988 0.280273 37.8205 0.280273C38.1422 0.280273 38.4507 0.408069 38.6782 0.635545C38.9057 0.863022 39.0335 1.17155 39.0335 1.49325V8.30167C39.0341 8.94874 39.2915 9.56911 39.749 10.0267C40.2066 10.4842 40.8269 10.7415 41.474 10.7422H48.7203C49.042 10.7422 49.3505 10.87 49.578 11.0974C49.8055 11.3249 49.9333 11.6334 49.9333 11.9551C49.9333 12.2768 49.8055 12.5854 49.578 12.8129C49.3505 13.0403 49.042 13.1681 48.7203 13.1681Z"
          fill="currentColor"
        />
        <path
          d="M17.1575 40.3774C16.8358 40.3774 16.5273 40.2496 16.2998 40.0222C16.0723 39.7947 15.9445 39.4862 15.9445 39.1644V29.4036C15.9445 29.0819 16.0723 28.7734 16.2998 28.5459C16.5273 28.3185 16.8358 28.1907 17.1575 28.1907C17.4792 28.1907 17.7877 28.3185 18.0152 28.5459C18.2427 28.7734 18.3705 29.0819 18.3705 29.4036V39.1644C18.3705 39.4862 18.2427 39.7947 18.0152 40.0222C17.7877 40.2496 17.4792 40.3774 17.1575 40.3774Z"
          fill="currentColor"
        />
        <path
          d="M17.1757 36.1381C16.8552 36.1381 16.5478 36.0113 16.3205 35.7854C16.0933 35.5595 15.9646 35.2528 15.9627 34.9324C15.9627 34.913 15.9506 32.9201 15.9506 32.1583C15.9506 31.53 15.9445 29.4073 15.9445 29.4073C15.9445 29.0856 16.0723 28.7771 16.2998 28.5496C16.5273 28.3221 16.8358 28.1943 17.1575 28.1943H19.8746C22.0919 28.1943 23.8968 29.9738 23.8968 32.162C23.8968 34.3502 22.0919 36.1296 19.8746 36.1296C19.1334 36.1296 17.206 36.1417 17.183 36.1417L17.1757 36.1381ZM18.3741 30.6166C18.3741 31.2086 18.3741 31.8551 18.3741 32.1583C18.3741 32.5125 18.3741 33.1384 18.3802 33.7049H19.8721C20.7418 33.7 21.4696 32.9929 21.4696 32.1583C21.4696 31.3238 20.7418 30.6166 19.8733 30.6166H18.3741Z"
          fill="currentColor"
        />
        <path
          d="M29.73 35.3921C29.5283 35.3923 29.3296 35.3421 29.1522 35.2462C28.9747 35.1502 28.8239 35.0115 28.7135 34.8426L25.5938 30.0672C25.4235 29.7979 25.366 29.4725 25.4336 29.1612C25.5013 28.8499 25.6887 28.5777 25.9554 28.4034C26.222 28.2291 26.5466 28.1668 26.8588 28.2298C27.1711 28.2928 27.4461 28.4761 27.6243 28.7402L29.7252 31.9582L31.803 28.7668C31.8899 28.633 32.0023 28.5175 32.1338 28.4271C32.2653 28.3366 32.4134 28.273 32.5695 28.2398C32.7256 28.2065 32.8867 28.2044 33.0437 28.2334C33.2006 28.2625 33.3503 28.3221 33.4842 28.409C33.6181 28.4959 33.7335 28.6083 33.824 28.7398C33.9144 28.8714 33.978 29.0194 34.0113 29.1755C34.0445 29.3316 34.0467 29.4927 34.0176 29.6497C33.9886 29.8066 33.9289 29.9563 33.842 30.0902L30.7501 34.8402C30.64 35.0096 30.4894 35.1487 30.3119 35.2451C30.1344 35.3415 29.9356 35.392 29.7337 35.3921H29.73Z"
          fill="currentColor"
        />
        <path
          d="M29.7179 40.3776C29.3962 40.3776 29.0876 40.2498 28.8602 40.0223C28.6327 39.7948 28.5049 39.4863 28.5049 39.1646L28.5182 34.1781C28.5182 33.8564 28.646 33.5478 28.8735 33.3204C29.101 33.0929 29.4095 32.9651 29.7312 32.9651C30.0529 32.9651 30.3614 33.0929 30.5889 33.3204C30.8164 33.5478 30.9442 33.8564 30.9442 34.1781L30.9308 39.1682C30.9299 39.4893 30.8016 39.7969 30.5743 40.0236C30.3469 40.2503 30.0389 40.3776 29.7179 40.3776Z"
          fill="currentColor"
        />
        <path
          d="M6.10975 52.2791H4.24541C3.11946 52.2791 2.03962 51.8319 1.24345 51.0357C0.447283 50.2395 0 49.1597 0 48.0337C0 46.9078 0.447283 45.8279 1.24345 45.0318C2.03962 44.2356 3.11946 43.7883 4.24541 43.7883H9.75474C10.0764 43.7883 10.385 43.9161 10.6124 44.1436C10.8399 44.3711 10.9677 44.6796 10.9677 45.0013C10.9677 45.323 10.8399 45.6315 10.6124 45.859C10.385 46.0865 10.0764 46.2143 9.75474 46.2143H4.24541C3.76286 46.2143 3.30007 46.406 2.95886 46.7472C2.61764 47.0884 2.42595 47.5512 2.42595 48.0337C2.42595 48.5163 2.61764 48.9791 2.95886 49.3203C3.30007 49.6615 3.76286 49.8532 4.24541 49.8532H6.11339C6.43509 49.8532 6.74361 49.981 6.97109 50.2085C7.19857 50.4359 7.32636 50.7445 7.32636 51.0662C7.32636 51.3879 7.19857 51.6964 6.97109 51.9239C6.74361 52.1514 6.43509 52.2791 6.11339 52.2791H6.10975Z"
          fill="currentColor"
        />
        <path
          d="M1.22872 48.8975C0.90702 48.8975 0.598496 48.7697 0.371019 48.5423C0.143542 48.3148 0.0157471 48.0063 0.0157471 47.6846L0.067905 26.3362C0.069833 25.2115 0.517967 24.1336 1.31393 23.339C2.10989 22.5444 3.18862 22.0981 4.31331 22.0981L48.7846 22.0896C49.1063 22.0896 49.4148 22.2174 49.6423 22.4449C49.8698 22.6723 49.9976 22.9809 49.9976 23.3026V45.0015C49.9976 45.3232 49.8698 45.6317 49.6423 45.8592C49.4148 46.0866 49.1063 46.2144 48.7846 46.2144H5.52386C5.20216 46.2144 4.89364 46.0866 4.66616 45.8592C4.43868 45.6317 4.31089 45.3232 4.31089 45.0015C4.31089 44.6798 4.43868 44.3712 4.66616 44.1438C4.89364 43.9163 5.20216 43.7885 5.52386 43.7885H47.5692V24.5083L4.30967 24.5168C3.82712 24.5168 3.36434 24.7085 3.02312 25.0497C2.68191 25.3909 2.49021 25.8537 2.49021 26.3362L2.43806 47.6846C2.43806 48.0056 2.31076 48.3136 2.08407 48.541C1.85738 48.7684 1.54979 48.8966 1.22872 48.8975Z"
          fill="currentColor"
        />
      </svg>
    );
  }

  if (icon === "csv") {
    return (
      <svg
        className={` ${sizeClass} inline-block  `}
        aria-hidden="true"
        fill="currentColor"
        viewBox="0 0 50 63"
      >
        <path
          d="M42.6967 62.1044H13.464C11.5281 62.1021 9.67207 61.3321 8.30315 59.9632C6.93422 58.5942 6.16417 56.7382 6.16193 54.8023V45.2659C6.16193 44.9442 6.28972 44.6357 6.5172 44.4082C6.74467 44.1807 7.0532 44.0529 7.3749 44.0529C7.6966 44.0529 8.00513 44.1807 8.2326 44.4082C8.46008 44.6357 8.58787 44.9442 8.58787 45.2659V54.8023C8.58948 56.095 9.10373 57.3344 10.0178 58.2485C10.9319 59.1626 12.1713 59.6768 13.464 59.6784H42.6967C43.9896 59.6768 45.229 59.1626 46.1433 58.2485C47.0576 57.3345 47.5721 56.0951 47.5741 54.8023V43.8746C47.5741 43.5529 47.7019 43.2444 47.9293 43.0169C48.1568 42.7894 48.4653 42.6616 48.787 42.6616C49.1087 42.6616 49.4173 42.7894 49.6447 43.0169C49.8722 43.2444 50 43.5529 50 43.8746V54.8023C49.9975 56.7383 49.2271 58.5944 47.858 59.9632C46.4889 61.3321 44.6328 62.1021 42.6967 62.1044Z"
          fill="black"
        />
        <path
          d="M48.7822 41.6183C48.4605 41.6183 48.152 41.4906 47.9245 41.2631C47.697 41.0356 47.5692 40.7271 47.5692 40.4054V12.5967C47.5681 12.2529 47.4946 11.9131 47.3533 11.5995C47.212 11.286 47.0062 11.0058 46.7492 10.7773L38.0522 3.04699C37.6064 2.64832 37.0297 2.42731 36.4317 2.42595H14.677C13.0616 2.42852 11.5131 3.07163 10.3712 4.21425C9.22922 5.35686 8.58704 6.90572 8.58543 8.52114V23.3037C8.58543 23.6254 8.45764 23.9339 8.23016 24.1614C8.00268 24.3888 7.69416 24.5166 7.37246 24.5166C7.05076 24.5166 6.74223 24.3888 6.51476 24.1614C6.28728 23.9339 6.15948 23.6254 6.15948 23.3037V8.52114C6.16173 6.26251 7.05971 4.09698 8.65646 2.49955C10.2532 0.902118 12.4184 0.0032109 14.677 9.10874e-08H36.4317C37.6233 -0.000230408 38.7736 0.437008 39.6643 1.22874L48.3613 8.96024C48.8752 9.41695 49.2866 9.97738 49.5682 10.6046C49.8498 11.2318 49.9953 11.9116 49.9952 12.5992V40.4054C49.9952 40.7271 49.8674 41.0356 49.6399 41.2631C49.4124 41.4906 49.1039 41.6183 48.7822 41.6183Z"
          fill="black"
        />
        <path
          d="M48.7203 13.1681H41.474C40.1838 13.1665 38.947 12.6533 38.0347 11.741C37.1224 10.8287 36.6091 9.59184 36.6075 8.30167V1.49325C36.6075 1.17155 36.7353 0.863022 36.9628 0.635545C37.1903 0.408069 37.4988 0.280273 37.8205 0.280273C38.1422 0.280273 38.4507 0.408069 38.6782 0.635545C38.9057 0.863022 39.0335 1.17155 39.0335 1.49325V8.30167C39.0341 8.94874 39.2915 9.56911 39.749 10.0267C40.2066 10.4842 40.8269 10.7415 41.474 10.7422H48.7203C49.042 10.7422 49.3505 10.87 49.578 11.0974C49.8055 11.3249 49.9333 11.6334 49.9333 11.9551C49.9333 12.2768 49.8055 12.5854 49.578 12.8129C49.3505 13.0403 49.042 13.1681 48.7203 13.1681Z"
          fill="black"
        />
        <path
          d="M6.10975 52.2791H4.24541C3.11946 52.2791 2.03962 51.8319 1.24345 51.0357C0.447283 50.2395 0 49.1597 0 48.0337C0 46.9078 0.447283 45.8279 1.24345 45.0318C2.03962 44.2356 3.11946 43.7883 4.24541 43.7883H9.75474C10.0764 43.7883 10.385 43.9161 10.6124 44.1436C10.8399 44.3711 10.9677 44.6796 10.9677 45.0013C10.9677 45.323 10.8399 45.6315 10.6124 45.859C10.385 46.0865 10.0764 46.2143 9.75474 46.2143H4.24541C3.76286 46.2143 3.30007 46.406 2.95886 46.7472C2.61764 47.0884 2.42595 47.5512 2.42595 48.0337C2.42595 48.5163 2.61764 48.9791 2.95886 49.3203C3.30007 49.6615 3.76286 49.8532 4.24541 49.8532H6.11339C6.43509 49.8532 6.74361 49.981 6.97109 50.2085C7.19857 50.4359 7.32636 50.7445 7.32636 51.0662C7.32636 51.3879 7.19857 51.6964 6.97109 51.9239C6.74361 52.1514 6.43509 52.2791 6.11339 52.2791H6.10975Z"
          fill="black"
        />
        <path
          d="M1.22872 48.8975C0.90702 48.8975 0.598496 48.7697 0.371019 48.5423C0.143542 48.3148 0.0157471 48.0063 0.0157471 47.6846L0.067905 26.3362C0.069833 25.2115 0.517967 24.1336 1.31393 23.339C2.10989 22.5444 3.18862 22.0981 4.31331 22.0981L48.7846 22.0896C49.1063 22.0896 49.4148 22.2174 49.6423 22.4449C49.8698 22.6723 49.9976 22.9809 49.9976 23.3026V45.0015C49.9976 45.3232 49.8698 45.6317 49.6423 45.8592C49.4148 46.0866 49.1063 46.2144 48.7846 46.2144H5.52386C5.20216 46.2144 4.89364 46.0866 4.66616 45.8592C4.43868 45.6317 4.31089 45.3232 4.31089 45.0015C4.31089 44.6798 4.43868 44.3712 4.66616 44.1438C4.89364 43.9163 5.20216 43.7885 5.52386 43.7885H47.5692V24.5083L4.30967 24.5168C3.82712 24.5168 3.36434 24.7085 3.02312 25.0497C2.68191 25.3909 2.49021 25.8537 2.49021 26.3362L2.43806 47.6846C2.43806 48.0056 2.31076 48.3136 2.08407 48.541C1.85738 48.7684 1.54979 48.8966 1.22872 48.8975Z"
          fill="black"
        />
        <path
          d="M18.1587 36.5474C18.4077 36.5474 18.6291 36.4948 18.8228 36.3896C19.022 36.2845 19.1797 36.1213 19.2959 35.8999C19.4121 35.673 19.4757 35.3797 19.4868 35.02H21.3047C21.2936 35.6564 21.147 36.2126 20.8647 36.6885C20.5825 37.1589 20.2062 37.5241 19.7358 37.7842C19.271 38.0387 18.7536 38.166 18.1836 38.166C17.5915 38.166 17.0741 38.0719 16.6313 37.8838C16.1942 37.6901 15.8317 37.4106 15.5439 37.0454C15.2562 36.6802 15.0404 36.2375 14.8965 35.7173C14.7581 35.1916 14.689 34.5911 14.689 33.916V33.1025C14.689 32.4329 14.7581 31.8353 14.8965 31.3096C15.0404 30.7839 15.2562 30.3384 15.5439 29.9731C15.8317 29.6079 16.1942 29.3312 16.6313 29.1431C17.0685 28.9494 17.5832 28.8525 18.1753 28.8525C18.8062 28.8525 19.3512 28.9854 19.8105 29.251C20.2754 29.5111 20.6379 29.8929 20.8979 30.3965C21.158 30.9001 21.2936 31.5171 21.3047 32.2476H19.4868C19.4757 31.8602 19.4176 31.5365 19.3125 31.2764C19.2074 31.0107 19.0579 30.8115 18.8643 30.6787C18.6761 30.5459 18.4382 30.4795 18.1504 30.4795C17.835 30.4795 17.5749 30.5404 17.3701 30.6621C17.1709 30.7783 17.016 30.9499 16.9053 31.1768C16.8001 31.4036 16.7254 31.6803 16.6812 32.0068C16.6424 32.3278 16.623 32.693 16.623 33.1025V33.916C16.623 34.3366 16.6424 34.7101 16.6812 35.0366C16.7199 35.3576 16.7918 35.6315 16.897 35.8584C17.0076 36.0853 17.1654 36.2568 17.3701 36.373C17.5749 36.4893 17.8377 36.5474 18.1587 36.5474ZM26.9658 35.6343C26.9658 35.4461 26.9105 35.2801 26.7998 35.1362C26.6947 34.9868 26.5231 34.8402 26.2852 34.6963C26.0472 34.5524 25.729 34.3975 25.3306 34.2314C24.9155 34.0599 24.5475 33.8883 24.2266 33.7168C23.9056 33.5452 23.6344 33.3571 23.4131 33.1523C23.1917 32.9421 23.0229 32.7013 22.9067 32.4302C22.7905 32.159 22.7324 31.8436 22.7324 31.4839C22.7324 31.1131 22.8016 30.77 22.9399 30.4546C23.0783 30.1392 23.2775 29.8625 23.5376 29.6245C23.7977 29.381 24.1104 29.1929 24.4756 29.0601C24.8408 28.9217 25.2531 28.8525 25.7124 28.8525C26.3599 28.8525 26.9132 28.9715 27.3726 29.2095C27.8374 29.4419 28.1916 29.7684 28.4351 30.189C28.6841 30.604 28.8086 31.0827 28.8086 31.625H26.8745C26.8745 31.3981 26.833 31.1934 26.75 31.0107C26.667 30.8226 26.5397 30.6732 26.3682 30.5625C26.1966 30.4463 25.978 30.3882 25.7124 30.3882C25.4689 30.3882 25.2642 30.4352 25.0981 30.5293C24.9377 30.6178 24.8159 30.7396 24.7329 30.8945C24.6554 31.0439 24.6167 31.2127 24.6167 31.4009C24.6167 31.5392 24.6416 31.661 24.6914 31.7661C24.7412 31.8713 24.8242 31.9736 24.9404 32.0732C25.0566 32.1673 25.2116 32.2642 25.4053 32.3638C25.6045 32.4634 25.8563 32.5768 26.1606 32.7041C26.7638 32.9365 27.2646 33.1772 27.6631 33.4263C28.0615 33.6753 28.3604 33.9658 28.5596 34.2979C28.7588 34.6299 28.8584 35.0422 28.8584 35.5347C28.8584 35.9331 28.7837 36.2928 28.6343 36.6138C28.4904 36.9347 28.2801 37.2114 28.0034 37.4438C27.7323 37.6763 27.403 37.8561 27.0156 37.9834C26.6338 38.1051 26.2077 38.166 25.7373 38.166C25.0345 38.166 24.4396 38.0277 23.9526 37.751C23.4712 37.4688 23.106 37.1063 22.8569 36.6636C22.6079 36.2209 22.4834 35.7533 22.4834 35.2607H24.3511C24.3677 35.6149 24.4424 35.8916 24.5752 36.0908C24.7135 36.29 24.8879 36.4284 25.0981 36.5059C25.3084 36.5778 25.527 36.6138 25.7539 36.6138C26.0251 36.6138 26.2492 36.5778 26.4263 36.5059C26.6034 36.4284 26.7362 36.3149 26.8247 36.1655C26.9188 36.0161 26.9658 35.839 26.9658 35.6343ZM33.0503 36.3896L34.7104 29.0186H36.7109L34.1543 38H32.9175L33.0503 36.3896ZM31.8716 29.0186L33.5898 36.4146L33.6729 38H32.4443L29.8711 29.0186H31.8716Z"
          fill="black"
        />
      </svg>
    );
  }

  if (icon === "pdf") {
    return (
      <svg
        className={` ${sizeClass} inline-block  `}
        aria-hidden="true"
        fill="currentColor"
        viewBox="0 0 50 63"
      >
        <path
          d="M42.6966 62.1044H13.464C11.528 62.1021 9.67201 61.3321 8.30308 59.9632C6.93416 58.5942 6.16411 56.7382 6.16187 54.8023V45.2659C6.16187 44.9442 6.28966 44.6357 6.51714 44.4082C6.74461 44.1807 7.05314 44.0529 7.37484 44.0529C7.69654 44.0529 8.00507 44.1807 8.23254 44.4082C8.46002 44.6357 8.58781 44.9442 8.58781 45.2659V54.8023C8.58942 56.095 9.10367 57.3344 10.0178 58.2485C10.9319 59.1626 12.1712 59.6768 13.464 59.6784H42.6966C43.9895 59.6768 45.229 59.1626 46.1433 58.2485C47.0576 57.3345 47.5721 56.0951 47.574 54.8023V43.8746C47.574 43.5529 47.7018 43.2444 47.9293 43.0169C48.1568 42.7894 48.4653 42.6616 48.787 42.6616C49.1087 42.6616 49.4172 42.7894 49.6447 43.0169C49.8722 43.2444 50 43.5529 50 43.8746V54.8023C49.9974 56.7383 49.2271 58.5944 47.858 59.9632C46.4888 61.3321 44.6327 62.1021 42.6966 62.1044Z"
          fill="currentColor"
        />
        <path
          d="M48.7821 41.6183C48.4604 41.6183 48.1519 41.4906 47.9244 41.2631C47.6969 41.0356 47.5691 40.7271 47.5691 40.4054V12.5967C47.5681 12.2529 47.4945 11.9131 47.3532 11.5995C47.2119 11.286 47.0061 11.0058 46.7492 10.7773L38.0521 3.04699C37.6064 2.64832 37.0297 2.42731 36.4316 2.42595H14.6769C13.0615 2.42852 11.513 3.07163 10.3711 4.21425C9.22916 5.35686 8.58698 6.90572 8.58537 8.52114V23.3037C8.58537 23.6254 8.45758 23.9339 8.2301 24.1614C8.00262 24.3888 7.6941 24.5166 7.3724 24.5166C7.0507 24.5166 6.74217 24.3888 6.5147 24.1614C6.28722 23.9339 6.15942 23.6254 6.15942 23.3037V8.52114C6.16167 6.26251 7.05965 4.09698 8.6564 2.49955C10.2532 0.902118 12.4183 0.0032109 14.6769 9.10874e-08H36.4316C37.6233 -0.000230408 38.7736 0.437008 39.6642 1.22874L48.3612 8.96024C48.8752 9.41695 49.2865 9.97738 49.5681 10.6046C49.8497 11.2318 49.9953 11.9116 49.9951 12.5992V40.4054C49.9951 40.7271 49.8673 41.0356 49.6398 41.2631C49.4123 41.4906 49.1038 41.6183 48.7821 41.6183Z"
          fill="currentColor"
        />
        <path
          d="M48.7203 13.1681H41.474C40.1838 13.1665 38.947 12.6533 38.0347 11.741C37.1224 10.8287 36.6091 9.59184 36.6075 8.30167V1.49325C36.6075 1.17155 36.7353 0.863022 36.9628 0.635545C37.1903 0.408069 37.4988 0.280273 37.8205 0.280273C38.1422 0.280273 38.4507 0.408069 38.6782 0.635545C38.9057 0.863022 39.0335 1.17155 39.0335 1.49325V8.30167C39.0341 8.94874 39.2915 9.56911 39.749 10.0267C40.2066 10.4842 40.8269 10.7415 41.474 10.7422H48.7203C49.042 10.7422 49.3505 10.87 49.578 11.0974C49.8055 11.3249 49.9333 11.6334 49.9333 11.9551C49.9333 12.2768 49.8055 12.5854 49.578 12.8129C49.3505 13.0403 49.042 13.1681 48.7203 13.1681Z"
          fill="currentColor"
        />
        <path
          d="M34.2362 40.3774C33.9145 40.3774 33.6059 40.2496 33.3785 40.0222C33.151 39.7947 33.0232 39.4862 33.0232 39.1644V29.4036C33.0232 29.0819 33.151 28.7734 33.3785 28.5459C33.6059 28.3185 33.9145 28.1907 34.2362 28.1907H38.1929C38.5146 28.1907 38.8231 28.3185 39.0506 28.5459C39.2781 28.7734 39.4059 29.0819 39.4059 29.4036C39.4059 29.7253 39.2781 30.0339 39.0506 30.2613C38.8231 30.4888 38.5146 30.6166 38.1929 30.6166H35.4491V39.1644C35.4491 39.4862 35.3213 39.7947 35.0939 40.0222C34.8664 40.2496 34.5579 40.3774 34.2362 40.3774Z"
          fill="currentColor"
        />
        <path
          d="M37.8788 35.4042H34.2398C33.9181 35.4042 33.6096 35.2764 33.3821 35.0489C33.1546 34.8215 33.0269 34.5129 33.0269 34.1912C33.0269 33.8695 33.1546 33.561 33.3821 33.3335C33.6096 33.1061 33.9181 32.9783 34.2398 32.9783H37.8788C38.2005 32.9783 38.509 33.1061 38.7365 33.3335C38.9639 33.561 39.0917 33.8695 39.0917 34.1912C39.0917 34.5129 38.9639 34.8215 38.7365 35.0489C38.509 35.2764 38.2005 35.4042 37.8788 35.4042Z"
          fill="currentColor"
        />
        <path
          d="M22.161 40.2198C21.8393 40.2198 21.5308 40.092 21.3033 39.8645C21.0759 39.6371 20.9481 39.3285 20.9481 39.0068V29.4146C20.9481 29.0929 21.0759 28.7844 21.3033 28.5569C21.5308 28.3295 21.8393 28.2017 22.161 28.2017C22.4827 28.2017 22.7913 28.3295 23.0187 28.5569C23.2462 28.7844 23.374 29.0929 23.374 29.4146V39.0068C23.374 39.3285 23.2462 39.6371 23.0187 39.8645C22.7913 40.092 22.4827 40.2198 22.161 40.2198Z"
          fill="currentColor"
        />
        <path
          d="M22.1817 40.3774C21.86 40.3774 21.5514 40.2496 21.324 40.0221C21.0965 39.7947 20.9687 39.4861 20.9687 39.1644C20.9687 39.1293 20.9553 35.6104 20.9553 34.2689C20.9553 33.1554 20.9481 29.4012 20.9481 29.4012C20.9481 29.0795 21.0759 28.771 21.3033 28.5435C21.5308 28.316 21.8393 28.1882 22.161 28.1882H24.9254C28.0088 28.1882 30.0805 30.6372 30.0805 34.2822C30.0805 37.7489 27.9554 40.3022 25.0285 40.3531C24.2401 40.3677 22.269 40.375 22.1853 40.375L22.1817 40.3774ZM23.3764 30.6166C23.3764 31.8162 23.3764 33.5714 23.3764 34.2737C23.3764 35.1082 23.3764 36.7906 23.3849 37.9454C23.9672 37.9454 24.6149 37.9369 24.9812 37.9308C26.8249 37.8981 27.6497 36.0762 27.6497 34.2846C27.6497 32.5113 26.9329 30.6166 24.9205 30.6166H23.3764Z"
          fill="currentColor"
        />
        <path
          d="M11.7865 40.3774C11.4648 40.3774 11.1562 40.2496 10.9288 40.0222C10.7013 39.7947 10.5735 39.4862 10.5735 39.1644V29.4036C10.5735 29.0819 10.7013 28.7734 10.9288 28.5459C11.1562 28.3185 11.4648 28.1907 11.7865 28.1907C12.1082 28.1907 12.4167 28.3185 12.6442 28.5459C12.8716 28.7734 12.9994 29.0819 12.9994 29.4036V39.1644C12.9994 39.4862 12.8716 39.7947 12.6442 40.0222C12.4167 40.2496 12.1082 40.3774 11.7865 40.3774Z"
          fill="currentColor"
        />
        <path
          d="M11.8047 36.1381C11.4842 36.1381 11.1768 36.0113 10.9496 35.7854C10.7223 35.5595 10.5936 35.2528 10.5917 34.9324C10.5917 34.913 10.5796 32.9201 10.5796 32.1583C10.5796 31.53 10.5796 29.4073 10.5796 29.4073C10.5796 29.0856 10.7074 28.7771 10.9349 28.5496C11.1623 28.3221 11.4709 28.1943 11.7926 28.1943H14.5096C16.7269 28.1943 18.5318 29.9738 18.5318 32.162C18.5318 34.3502 16.7269 36.1296 14.5096 36.1296C13.7685 36.1296 11.8411 36.1417 11.8192 36.1417L11.8047 36.1381ZM13.0031 30.6166C13.0031 31.2086 13.0031 31.8563 13.0031 32.1583C13.0031 32.5125 13.0031 33.1384 13.0031 33.7049H14.4951C15.3599 33.7049 16.0913 32.9989 16.0913 32.1632C16.0913 31.3274 15.3636 30.6215 14.4951 30.6215L13.0031 30.6166Z"
          fill="currentColor"
        />
        <path
          d="M6.10975 52.2791H4.24541C3.11946 52.2791 2.03962 51.8319 1.24345 51.0357C0.447283 50.2395 0 49.1597 0 48.0337C0 46.9078 0.447283 45.8279 1.24345 45.0318C2.03962 44.2356 3.11946 43.7883 4.24541 43.7883H9.75474C10.0764 43.7883 10.385 43.9161 10.6124 44.1436C10.8399 44.3711 10.9677 44.6796 10.9677 45.0013C10.9677 45.323 10.8399 45.6315 10.6124 45.859C10.385 46.0865 10.0764 46.2143 9.75474 46.2143H4.24541C3.76286 46.2143 3.30007 46.406 2.95886 46.7472C2.61764 47.0884 2.42595 47.5512 2.42595 48.0337C2.42595 48.5163 2.61764 48.9791 2.95886 49.3203C3.30007 49.6615 3.76286 49.8532 4.24541 49.8532H6.11339C6.43509 49.8532 6.74361 49.981 6.97109 50.2085C7.19857 50.4359 7.32636 50.7445 7.32636 51.0662C7.32636 51.3879 7.19857 51.6964 6.97109 51.9239C6.74361 52.1514 6.43509 52.2791 6.11339 52.2791H6.10975Z"
          fill="currentColor"
        />
        <path
          d="M1.22872 48.8973C0.90702 48.8973 0.598496 48.7695 0.371019 48.542C0.143542 48.3145 0.0157471 48.006 0.0157471 47.6843L0.067905 26.336C0.069833 25.2113 0.517967 24.1333 1.31393 23.3387C2.10989 22.5441 3.18862 22.0978 4.31331 22.0978L48.7846 22.0894C49.1063 22.0894 49.4148 22.2171 49.6423 22.4446C49.8698 22.6721 49.9976 22.9806 49.9976 23.3023V45.0012C49.9976 45.3229 49.8698 45.6314 49.6423 45.8589C49.4148 46.0864 49.1063 46.2142 48.7846 46.2142H5.52386C5.20216 46.2142 4.89364 46.0864 4.66616 45.8589C4.43868 45.6314 4.31089 45.3229 4.31089 45.0012C4.31089 44.6795 4.43868 44.371 4.66616 44.1435C4.89364 43.916 5.20216 43.7882 5.52386 43.7882H47.5692V24.508L4.30967 24.5165C3.82712 24.5165 3.36434 24.7082 3.02312 25.0494C2.68191 25.3906 2.49021 25.8534 2.49021 26.336L2.43806 47.6843C2.43806 48.0054 2.31076 48.3134 2.08407 48.5407C1.85738 48.7681 1.54979 48.8963 1.22872 48.8973Z"
          fill="currentColor"
        />
      </svg>
    );
  }

  if (icon === "microsoft") {
    return (
      <svg
        className={` ${sizeClass} inline-block  `}
        fill="currentColor"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 23 23"
      >
        <g clipPath="url(#clip0_616_221)">
          {/* <path d="M0 0H23V23H0V0Z" fill="currentColor" /> */}
          <path d="M1 1H11V11H1V1Z" fill="#F35325" />
          <path d="M12 1H22V11H12V1Z" fill="#81BC06" />
          <path d="M1 12H11V22H1V12Z" fill="#05A6F0" />
          <path d="M12 12H22V22H12V12Z" fill="#FFBA08" />
        </g>
        <defs>
          <clipPath id="clip0_616_221">
            <rect width="23" height="23" fill="white" />
          </clipPath>
        </defs>
      </svg>
    );
  }

  if (icon === "loading") {
    return (
      <svg
        className={` ${sizeClass} inline-block animate-spin  `}
        xmlns="http://www.w3.org/2000/svg"
        fill="currentColor"
        viewBox="0 0 24 24"
      >
        <path d="M11 3c-1.613 0-3.122.437-4.432 1.185l1.65 2.445-6.702-.378 2.226-6.252 1.703 2.522c1.633-.959 3.525-1.522 5.555-1.522 4.406 0 8.197 2.598 9.953 6.34l-1.642 1.215c-1.355-3.258-4.569-5.555-8.311-5.555zm13 12.486l-2.375-6.157-5.307 3.925 3.389.984c-.982 3.811-4.396 6.651-8.488 6.75l.891 1.955c4.609-.461 8.373-3.774 9.521-8.146l2.369.689zm-18.117 3.906c-2.344-1.625-3.883-4.33-3.883-7.392 0-1.314.29-2.56.799-3.687l-2.108-.12c-.439 1.188-.691 2.467-.691 3.807 0 3.831 1.965 7.192 4.936 9.158l-1.524 2.842 6.516-1.044-2.735-6.006-1.31 2.442z" />
      </svg>
    );
  }
  if (icon === "app") {
    return (
      <svg
        className={` ${sizeClass} inline-block  `}
        xmlns="http://www.w3.org/2000/svg"
        fill="currentColor"
        viewBox="0 0 290 264"
      >
        <path
          d="M112.233 104.244C106.455 104.242 100.778 105.756 95.7684 108.635C90.7586 111.513 86.5912 115.655 83.6823 120.647L0 264H38.456C44.2308 263.999 49.9048 262.486 54.9137 259.613C59.9226 256.739 64.0919 252.603 67.0068 247.618L86.2185 214.713L97.1033 196.079L141.807 119.548L150.733 104.244H112.233Z"
          fill="url(#paint0_linear_149_456)"
        />
        <path
          d="M111.547 33.2857L130.813 0L212.939 144.278C215.795 149.3 217.285 154.982 217.262 160.759C217.239 166.535 215.704 172.205 212.809 177.205L193.532 210.49L111.417 66.2122C108.559 61.1911 107.068 55.5088 107.091 49.7316C107.114 43.9544 108.65 38.284 111.547 33.2857Z"
          fill="url(#paint1_linear_149_456)"
        />
        <path
          d="M289.285 245.714H123.281C117.498 245.714 111.815 244.199 106.8 241.319C101.785 238.439 97.6121 234.295 94.6976 229.3L86.1748 214.714L97.0596 196.079H241.348C247.134 196.075 252.82 197.588 257.837 200.468C262.855 203.349 267.029 207.495 269.943 212.493L289.285 245.714Z"
          fill="url(#paint2_linear_149_456)"
        />
        <defs>
          <linearGradient
            id="paint0_linear_149_456"
            x1="116.173"
            y1="107.901"
            x2="37.3131"
            y2="255.118"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#2314CC" />
            <stop offset="0.22" stopColor="#234CE4" />
            <stop offset="1" stopColor="#4081FF" />
          </linearGradient>
          <linearGradient
            id="paint1_linear_149_456"
            x1="200.792"
            y1="184.508"
            x2="134.199"
            y2="47.8169"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#7215D4" />
            <stop offset="0.11" stopColor="#7554D5" />
            <stop offset="0.56" stopColor="#9E8AE9" />
            <stop offset="1" stopColor="#CC99FF" />
          </linearGradient>
          <linearGradient
            id="paint2_linear_149_456"
            x1="107.651"
            y1="220.896"
            x2="271.108"
            y2="220.896"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#2E31F0" />
            <stop offset="0.2" stopColor="#4081FF" />
            <stop offset="0.39" stopColor="#848EE5" />
            <stop offset="0.49" stopColor="#8183E2" />
            <stop offset="0.65" stopColor="#7866DA" />
            <stop offset="0.75" stopColor="#7251D4" />
          </linearGradient>
        </defs>
      </svg>
    );
  }

  return (
    <svg
      className={` ${sizeClass} inline-block  `}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
    >
      <path d="M1 3.488c0-1.926 4.656-3.488 10-3.488 5.345 0 10 1.562 10 3.488s-4.655 3.487-10 3.487c-5.344 0-10-1.561-10-3.487zm10 9.158c5.345 0 10-1.562 10-3.487v-2.44c-2.418 1.738-7.005 2.256-10 2.256-3.006 0-7.588-.523-10-2.256v2.44c0 1.926 4.656 3.487 10 3.487zm0 5.665c.34 0 .678-.007 1.011-.019.045-1.407.537-2.7 1.342-3.745-.839.067-1.643.1-2.353.1-3.006 0-7.588-.523-10-2.256v2.434c0 1.925 4.656 3.486 10 3.486zm1.254 1.97c-.438.02-.861.03-1.254.03-2.995 0-7.582-.518-10-2.256v2.458c0 1.925 4.656 3.487 10 3.487 1.284 0 2.526-.092 3.676-.256-1.155-.844-2.02-2.055-2.422-3.463zm10.746-1.781c0 2.485-2.017 4.5-4.5 4.5s-4.5-2.015-4.5-4.5 2.017-4.5 4.5-4.5 4.5 2.015 4.5 4.5zm-2.166-1.289l-2.063.557.916-1.925-1.387.392-1.466 3.034 1.739-.472-1.177 2.545 3.438-4.131z" />
    </svg>
  );
};
export default Icon;
