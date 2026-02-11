import imgEdison from "figma:asset/1cceea09534772c1da677699f6766a61109c457c.png";
import imgUserAvatar from "figma:asset/1d1c6e47491f6726f6303aa8c515da81db485c50.png";

export default function VerticalSidebar() {
  return (
    <div className="absolute left-0 top-0 w-20 h-full bg-[#212121] flex flex-col items-center">
      <div className="w-[72px] h-[70px] mt-2 overflow-hidden">
        <img src={imgEdison} alt="Edison" className="w-full h-auto object-contain" />
      </div>
      
      {/* Add buttons */}
      <button className="mt-12 w-[53px] h-[51px] bg-[#171717] border border-[#484460] rounded-lg text-[#c0bdcf] text-3xl font-medium">
        +
      </button>
      <button className="mt-2 w-[53px] h-[51px] bg-[#171717] border border-[#484460] rounded-lg text-[#c0bdcf] text-3xl font-medium">
        +
      </button>
      <button className="mt-2 w-[53px] h-[51px] bg-[#171717] border border-white rounded-lg text-[#c0bdcf] text-3xl font-medium">
        +
      </button>

      {/* User Avatar */}
      <div className="mt-auto mb-24">
        <img src={imgUserAvatar} alt="User" className="w-[47px] h-[44px] rounded-full border border-[#6a9c9e]" />
      </div>
    </div>
  );
}
