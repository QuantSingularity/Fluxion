import { ethers } from "ethers";

export const SYNTHETIC_ABI = [
  "event SyntheticAssetCreated(address indexed assetAddress, string assetId, address oracle, bytes32 jobId, uint256 paymentAmount)",
  "function createSynthetic(string memory assetId, address oracle, bytes32 jobId, uint256 paymentAmount) external returns (address)",
  "function getSyntheticAsset(string memory assetId) external view returns (address)",
  "function syntheticAssetExists(string memory assetId) external view returns (bool)",
  "function setFee(uint256 newFee) external",
  "function withdrawFees() external",
  "function owner() external view returns (address)",
  "function transferOwnership(address newOwner) external",
];

export async function createSyntheticAsset(provider, params) {
  if (!provider || !params) {
    throw new Error("Missing provider or params for createSyntheticAsset");
  }

  const factoryAddress = import.meta.env?.VITE_FACTORY_ADDRESS;
  if (!factoryAddress) {
    throw new Error("VITE_FACTORY_ADDRESS not configured");
  }

  const signer = await provider.getSigner(); // ethers v6 uses await
  const factory = new ethers.Contract(factoryAddress, SYNTHETIC_ABI, signer);

  try {
    // ethers v6: ethers.parseEther (not ethers.utils.parseEther)
    const tx = await factory.createSynthetic(
      params.assetId,
      params.oracle,
      params.jobId,
      ethers.parseEther(params.payment.toString()),
    );
    return tx.wait();
  } catch (error) {
    console.error("Error creating synthetic asset:", error);
    throw error;
  }
}
